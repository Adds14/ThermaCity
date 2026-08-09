import { useState } from 'react';
import HeatMap from '../components/Map/HeatMap';
import ScenarioPanel from '../components/Map/ScenarioPanel';
import './MapView.css';

export default function MapView() {
  const [selectedYear, setSelectedYear] = useState(2024);
  const [selectedCell, setSelectedCell] = useState(null);

  return (
    <div className="map-view-container">
      <HeatMap year={selectedYear} onCellSelect={(cell) => setSelectedCell(cell)} />
      <div className="scenario-overlay">
        <ScenarioPanel year={selectedYear} selectedCell={selectedCell} />
      </div>
    </div>
  );
}
