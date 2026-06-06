# Testing the Production Stack with Oracle Cloud and Tailscale

This guide describes how to test the production Caddy configuration — including
TLS certificate provisioning — when your primary IP address already has a
reverse proxy occupying ports 80 and 443.

## Overview

The production `Caddyfile.prod` manages its own TLS certificates via Let's
Encrypt HTTP-01 challenge, which requires Caddy to own ports 80 and 443
directly. If those ports are taken by another reverse proxy (e.g. nginx), you
cannot run the prod stack on the same IP.

The solution is a **TCP passthrough gateway**: a cheap VM with a clean public IP
that forwards raw TCP traffic to your local machine over Tailscale. The VM never
terminates TLS — it just forwards bytes. Caddy on your local machine handles the
ACME challenge and all TLS termination exactly as it would in real production.

```
Internet → Oracle VM (public IP, TCP forward only) → Tailscale → Local machine (Caddy)
```

## Prerequisites

- Oracle Cloud account (free tier is sufficient)
- Tailscale account (free tier is sufficient)
- A test domain managed in Cloudflare with the proxy disabled (grey cloud)

## Phase 1: Provision the Oracle VM

1. In the Oracle Cloud Console go to **Compute → Instances → Create Instance**
2. Choose shape **VM.Standard.E2.1.Micro** (AMD) — this is the Always Free shape
3. Image: **Ubuntu 24.04**
4. Under "Add SSH Keys" paste your public key
5. Click Create and note the **Public IP** from the instance details page

## Phase 2: Open Firewall Ports

Two layers must both be opened.

**Oracle Security List** (in the console):

- Go to Networking → Virtual Cloud Networks → your VCN → Security Lists → Default
- Add two Ingress Rules:
  - Source `0.0.0.0/0`, Protocol TCP, Destination Port `80`
  - Source `0.0.0.0/0`, Protocol TCP, Destination Port `443`

**OS-level firewall** on the VM (Oracle Ubuntu images block all inbound by
default — this is the most common setup failure):

```bash
ssh ubuntu@<oracle-public-ip>
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo apt install iptables-persistent -y
sudo netfilter-persistent save
```

## Phase 3: Install Tailscale on Both Machines

**On the Oracle VM:**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Follow the auth URL printed to the terminal to approve the machine
```

**On your local machine** (the one that will run Caddy):

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Note your local machine's Tailscale IP:

```bash
tailscale ip -4   # e.g. 100.64.x.x
```

## Phase 4: Configure TCP Forwarding on the Oracle VM

This configures the VM as a pure TCP forwarder. It forwards inbound traffic on
ports 80 and 443 to your local machine over the Tailscale network without
inspecting or terminating TLS.

```bash
# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Replace with your local machine's Tailscale IP
HOME_TS_IP=100.64.x.x

sudo iptables -t nat -A PREROUTING -p tcp --dport 80  -j DNAT --to-destination $HOME_TS_IP:80
sudo iptables -t nat -A PREROUTING -p tcp --dport 443 -j DNAT --to-destination $HOME_TS_IP:443
sudo iptables -t nat -A POSTROUTING -j MASQUERADE
sudo netfilter-persistent save
```

## Phase 5: Bind Caddy to the Tailscale Interface

Your local nginx already owns `0.0.0.0:80/443`. Caddy must bind only to the
Tailscale IP so the two do not conflict. Create a local override compose file
(do not edit `compose.prod.yaml`):

```yaml
# compose.prod-test.yaml
services:
  frontend:
    ports:
      - '100.64.x.x:80:80' # your local Tailscale IP
      - '100.64.x.x:443:443'
      - '100.64.x.x:443:443/udp'
```

Run the stack with the override applied:

```bash
docker compose \
  -f compose.yaml \
  -f compose.prod.yaml \
  -f compose.prod-test.yaml \
  --env-file config/env/env.prod.local \
  up -d
```

## Phase 6: Configure DNS

In Cloudflare, add an **A record** pointing your test subdomain to the Oracle
VM's public IP:

```
prod-test.yourdomain.com  →  <oracle-public-ip>
```

**Critical**: set the Cloudflare proxy status to **DNS only (grey cloud)**.
If the orange proxy is enabled, Cloudflare terminates TLS and Caddy never
receives the ACME challenge.

## Phase 7: Configure and Start the Stack

In `config/env/env.prod.local` set the test domain:

```bash
DOMAIN=prod-test.yourdomain.com
ACME_EMAIL=your@email.com
```

Start the stack and watch Caddy provision a certificate:

```bash
docker compose \
  -f compose.yaml \
  -f compose.prod.yaml \
  -f compose.prod-test.yaml \
  --env-file config/env/env.prod.local \
  up -d

docker compose logs -f frontend
```

Caddy will log the ACME challenge exchange and certificate issuance. Once
complete, `https://prod-test.yourdomain.com` should be accessible with a valid
Let's Encrypt certificate served by your local Caddy instance.

## Troubleshooting

**ACME challenge fails:**

- Confirm the Cloudflare proxy is grey (not orange)
- Verify the Oracle Security List has ports 80 and 443 open
- Verify the OS-level iptables rules are present: `sudo iptables -L INPUT -n`
- Verify forwarding is configured: `sudo iptables -t nat -L PREROUTING -n`
- Test that port 80 traffic reaches your local machine before starting Caddy:

  ```bash
  # On local machine, bind a test server to the Tailscale IP
  python3 -m http.server 80 --bind 100.64.x.x

  # From another machine, curl your test domain
  curl http://prod-test.yourdomain.com
  ```

**Port conflict with nginx:**

Confirm nginx is not binding to all interfaces on ports 80/443. In your nginx
config, `listen 80;` on many Linux distros binds dual-stack (IPv4 and IPv6) but
not the Tailscale interface. If there is still a conflict, explicitly set nginx
to IPv4-only by changing `listen 80;` to `listen 0.0.0.0:80;`.

**Tailscale connectivity:**

```bash
# On the Oracle VM, verify the local machine is reachable
ping 100.64.x.x

# Verify TCP forwarding is reachable on port 80
curl -v http://100.64.x.x
```
