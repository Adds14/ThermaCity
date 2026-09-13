import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import KnowYourHeat from './pages/KnowYourHeat';
import MapView from './pages/MapView';
import WardRankings from './components/Dashboard/WardRankings';
import ReportPage from './pages/ReportPage';
import CompareAreas from './pages/CompareAreas';
import HowItWorks from './pages/HowItWorks';
import DashboardLayout from './layouts/DashboardLayout';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/know-your-heat" element={<KnowYourHeat />} />
        <Route path="/compare" element={<CompareAreas />} />
        
        {/* GIS Dashboard Routes */}
        <Route path="/explore" element={<DashboardLayout />}>
          <Route path="map" element={<MapView />} />
          <Route path="rankings" element={<WardRankings />} />
          <Route path="reports" element={<ReportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
