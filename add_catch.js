const fs = require('fs');
let code = fs.readFileSync('frontend/src/components/Map/HeatMap.jsx', 'utf8');

const target = `if (layer.isPopupOpen()) layer.setPopupContent(updatedPopup);
                    }
                  });`;

const replacement = `if (layer.isPopupOpen()) layer.setPopupContent(updatedPopup);
                    }
                  }).catch(e => {
                    if (layer.isPopupOpen()) {
                      layer.setPopupContent(initialPopup.replace('<div class="spinner small"></div>', '').replace('Analyzing risk factors...', '<span style="color:var(--tier-stressed)">Risk analysis currently unavailable</span>'));
                    }
                  });`;

code = code.replace(target, replacement);
fs.writeFileSync('frontend/src/components/Map/HeatMap.jsx', code);
