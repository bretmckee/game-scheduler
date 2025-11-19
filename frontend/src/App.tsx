import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { theme } from './theme';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { AuthCallback } from './pages/AuthCallback';
import { GuildListPage } from './pages/GuildListPage';
import { GuildDashboard } from './pages/GuildDashboard';
import { GuildConfig } from './pages/GuildConfig';
import { ChannelConfig } from './pages/ChannelConfig';
import { BrowseGames } from './pages/BrowseGames';
import { GameDetails } from './pages/GameDetails';
import { CreateGame } from './pages/CreateGame';
import { MyGames } from './pages/MyGames';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            
            <Route element={<Layout />}>
              <Route path="/" element={<HomePage />} />
              
              <Route element={<ProtectedRoute />}>
                <Route path="/guilds" element={<GuildListPage />} />
                <Route path="/guilds/:guildId" element={<GuildDashboard />} />
                <Route path="/guilds/:guildId/config" element={<GuildConfig />} />
                <Route path="/channels/:channelId/config" element={<ChannelConfig />} />
                <Route path="/guilds/:guildId/games" element={<BrowseGames />} />
                <Route path="/guilds/:guildId/games/new" element={<CreateGame />} />
                <Route path="/games/:gameId" element={<GameDetails />} />
                <Route path="/my-games" element={<MyGames />} />
              </Route>
            </Route>
            
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
