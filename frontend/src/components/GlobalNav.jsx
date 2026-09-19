import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Layers, Menu, X, ThermometerSun } from 'lucide-react';
import './GlobalNav.css';

export default function GlobalNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const path = location.pathname;

  // Auto-close drawer when route changes
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  // Prevent background body scrolling while drawer is active
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  return (
    <nav className="global-nav">
      <div className="nav-brand">
        <Link to="/" onClick={() => setMobileMenuOpen(false)}>
          <Layers size={20} className="brand-icon" />
          THERMACITY
        </Link>
      </div>
      
      {/* Desktop Links (Hidden on Mobile) */}
      <div className="nav-links-center desktop-only">
        <Link to="/explore/map" className={path.startsWith('/explore') ? 'active' : ''}>Explore Heat</Link>
        <Link to="/compare" className={path === '/compare' ? 'active' : ''}>Compare Areas</Link>
        <Link to="/how-it-works" className={path === '/how-it-works' ? 'active' : ''}>How It Works</Link>
      </div>

      <div className="nav-actions desktop-only">
        <Link to="/know-your-heat" className="btn btn-primary btn-sm">Know Your Heat</Link>
      </div>

      {/* Mobile Top Controls: Heat Pill + Hamburger Toggle */}
      <div className="mobile-nav-right mobile-only">
        <Link to="/know-your-heat" className="mobile-heat-pill" title="Know Your Heat">
          <ThermometerSun size={16} />
          <span>Your Heat</span>
        </Link>
        <button
          className="mobile-menu-btn"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label={mobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Slide-in Mobile Drawer Overlay */}
      {mobileMenuOpen && (
        <div className="mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
          <div className="mobile-menu-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="mobile-menu-header">
              <div className="nav-brand">
                <Link to="/" onClick={() => setMobileMenuOpen(false)}>
                  <Layers size={20} className="brand-icon" />
                  THERMACITY
                </Link>
              </div>
              <button
                className="mobile-close-btn"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close menu"
              >
                <X size={20} />
              </button>
            </div>

            <div className="mobile-links-list">
              <Link to="/explore/map" onClick={() => setMobileMenuOpen(false)}>
                Explore Heat Map
              </Link>
              <Link to="/compare" onClick={() => setMobileMenuOpen(false)}>
                Compare Areas
              </Link>
              <Link to="/how-it-works" onClick={() => setMobileMenuOpen(false)}>
                How It Works
              </Link>
            </div>

            <div className="mobile-menu-footer">
              <Link
                to="/know-your-heat"
                className="btn btn-primary"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => setMobileMenuOpen(false)}
              >
                <ThermometerSun size={18} /> Know Your Heat
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
