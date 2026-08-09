import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';
import MapView from './pages/MapView';
import WardRankings from './components/Dashboard/WardRankings';
import ReportPage from './pages/ReportPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<MapView />} />
          <Route path="/ward/top" element={<WardRankings />} />
          <Route path="/report" element={<ReportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
