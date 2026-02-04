// Copyright 2025-2026 Bret McKee
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import { FC, useState } from 'react';
import { StatusCodes } from 'http-status-codes';
import { Button, CircularProgress } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import axios from 'axios';

interface ExportButtonProps {
  gameId: string;
}

export const ExportButton: FC<ExportButtonProps> = ({ gameId }) => {
  const [loading, setLoading] = useState(false);

  const downloadCalendar = async () => {
    setLoading(true);

    try {
      const url = `/api/v1/export/game/${gameId}`;

      const response = await axios.get(url, {
        responseType: 'blob',
        withCredentials: true,
      });

      // Extract filename from Content-Disposition header, fallback to generated name
      const contentDisposition = response.headers['content-disposition'];
      let filename = `game-${gameId}.ics`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=([^;]+)/);
        if (filenameMatch) {
          filename = filenameMatch[1].trim();
        }
      }

      const blob = new Blob([response.data], { type: 'text/calendar' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Failed to export calendar:', error);
      const errorMessage =
        (error as any).response?.status === StatusCodes.FORBIDDEN
          ? 'You must be the host or a participant to export this game.'
          : 'Failed to export calendar. Please try again.';
      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      variant="outlined"
      onClick={downloadCalendar}
      disabled={loading}
      startIcon={loading ? <CircularProgress size={20} /> : <DownloadIcon />}
    >
      Export to Calendar
    </Button>
  );
};
