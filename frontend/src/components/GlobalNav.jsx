import { Link, useLocation } from 'react-router-dom';
import { Layers } from 'lucide-react';
import './GlobalNav.css';

export default function GlobalNav() {
  const location = useLocation();
  const path = location.pathname;

  return (
    <nav className="global-nav">
      <div className="nav-brand">
        <Link to="/">
          <Layers size={20} className="brand-icon" />
          THERMACITY
        </Link>
      </div>
      
      <div className="nav-links-center">
        <Link to="/explore/map" className={path.startsWith('/explore') ? 'active' : ''}>Explore Heat</Link>
        <Link to="/compare" className={path === '/compare' ? 'active' : ''}>Compare Areas</Link>
        <Link to="/how-it-works" className={path === '/how-it-works' ? 'active' : ''}>How It Works</Link>
      </div>

      <div className="nav-actions">
        <Link to="/know-your-heat" className="btn btn-primary btn-sm">Know Your Heat</Link>
      </div>
    </nav>
  );
}
