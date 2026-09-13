import { BookOpen, ThermometerSun, Leaf, Droplets, Map, Activity } from 'lucide-react';
import GlobalNav from '../components/GlobalNav';
import './HowItWorks.css';

export default function HowItWorks() {
  return (
    <div className="hiw-container">
      <GlobalNav />
      
      <div className="hiw-content">
        <div className="hiw-header">
          <h1>The Science of Urban Heat</h1>
          <p>Understanding how ThermaCity measures and maps the micro-climates of Pune.</p>
        </div>

        <div className="timeline-layout">
          {/* Step 1 */}
          <div className="tl-step">
            <div className="tl-num">01</div>
            <div className="tl-card">
              <ThermometerSun className="tl-icon text-stressed" size={32} />
              <h2>What is Urban Heat?</h2>
              <p>
                Urban Heat Islands (UHI) are urbanized areas that experience higher temperatures than outlying areas. 
                Structures such as buildings, roads, and other infrastructure absorb and re-emit the sun's heat more 
                than natural landscapes such as forests and water bodies.
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="tl-step">
            <div className="tl-num">02</div>
            <div className="tl-card">
              <Activity className="tl-icon text-emergency" size={32} />
              <h2>Why cities become hotter</h2>
              <p>
                As cities grow, natural land cover is replaced by dense concentrations of pavement, buildings, and other surfaces 
                that absorb and retain heat. This effect is compounded by tall buildings providing multiple surfaces for the 
                reflection and absorption of sunlight, and blocking natural wind flow (the "urban canyon" effect).
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="tl-step">
            <div className="tl-num">03</div>
            <div className="tl-card">
              <Leaf className="tl-icon text-safe" size={32} />
              <h2>What factors influence local heat</h2>
              <p>
                Not all parts of a city are equally hot. Micro-climates are shaped by the exact composition of a neighbourhood.
                Parks, tree-lined streets, and lakes provide localized cooling through shading and evapotranspiration. 
                Conversely, dense industrial zones or large parking lots create intense localized heat traps.
              </p>
            </div>
          </div>

          {/* Step 4 */}
          <div className="tl-step">
            <div className="tl-num">04</div>
            <div className="tl-card">
              <Map className="tl-icon text-accent" size={32} />
              <h2>How ThermaCity measures it</h2>
              <p>
                ThermaCity divides Pune into a high-resolution 100×100 meter grid. For every single grid cell, we analyze 
                multispectral satellite imagery to extract four key indices: Land Surface Temperature (LST), Vegetation (NDVI), 
                Built-up surfaces (NDBI), and Water presence (NDWI).
              </p>
            </div>
          </div>

          {/* Step 5 */}
          <div className="tl-step">
            <div className="tl-num">05</div>
            <div className="tl-card">
              <BookOpen className="tl-icon text-muted" size={32} />
              <h2>How to interpret the Urban Heat Index</h2>
              <p>
                These four indices are mathematically combined and normalized into the ThermaCity Heat Vulnerability Index (HVI), 
                scored from 0 to 100. A score of 100 does not mean 100°C; rather, it indicates the highest relative heat vulnerability 
                within the city's boundaries. The index helps planners target cooling interventions where they are needed most.
              </p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
