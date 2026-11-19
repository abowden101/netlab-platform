import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Labs from './pages/Labs';
import LabSession from './pages/LabSession';
import InstructorDashboard from './pages/InstructorDashboard';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Labs />} />
        <Route path="/labs" element={<Labs />} />
        <Route path="/sessions/:sessionId" element={<LabSession />} />
        <Route path="/instructor" element={<InstructorDashboard />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
