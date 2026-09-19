import { useState } from 'react';
import { Sliders } from 'lucide-react';
import HeatMap from '../components/Map/HeatMap';
import ScenarioPanel from '../components/Map/ScenarioPanel';
import './MapView.css';

export default function MapView() {
  const [selectedYear, setSelectedYear] = useState(2026);
  const [selectedCell, setSelectedCell] = useState(null);
  const [panelOpen, setPanelOpen] = useState(false);

  return (
    <div className="map-view-container">
      <HeatMap year={selectedYear} onCellSelect={(cell) => setSelectedCell(cell)} />
      
      {/* Mobile Toggle Button */}
      <button 
        className="mobile-scenario-toggle"
        onClick={() => setPanelOpen(!panelOpen)}
      >
        <Sliders size={18} />
        {panelOpen ? 'Hide Simulator' : 'Simulate'}
      </button>

      <div className={`scenario-overlay ${panelOpen ? 'open' : 'closed'}`}>
        <ScenarioPanel year={selectedYear} selectedCell={selectedCell} />
      </div>
    </div>
  );
}
