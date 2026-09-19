import sys
with open('frontend/src/components/Map/HeatMap.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

target = """if (layer.isPopupOpen()) layer.setPopupContent(updatedPopup);
                    }
                  });"""

replacement = """if (layer.isPopupOpen()) layer.setPopupContent(updatedPopup);
                    }
                  }).catch(e => {
                    if (layer.isPopupOpen()) {
                      layer.setPopupContent(initialPopup.replace('<div class="spinner small"></div>', '').replace('Analyzing risk factors...', '<span style="color:var(--tier-stressed)">Risk analysis currently unavailable</span>'));
                    }
                  });"""

code = code.replace(target, replacement)

with open('frontend/src/components/Map/HeatMap.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
