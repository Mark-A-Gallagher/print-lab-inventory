import { Link, Outlet } from "react-router-dom";
import "./Layout.css";

export default function Layout() {
    return (
        <div className="layout">
            <nav className="navbar">
                <div className="navbar-container">
                    <Link to="/" className="navbar-brand">
                        3D Print Lab Inventory
                    </Link>
                    <ul className="nav-menu">
                        <li>
                            <Link to="/">Dashboard</Link>
                        </li>
                        <li>
                            <Link to="/inventory">Inventory</Link>
                        </li>
                        <li>
                            <Link to="/machines">Machines</Link>
                        </li>
                        <li>
                            <Link to="/requests">Print Requests</Link>
                        </li>
                    </ul>
                </div>
            </nav>
            <main className="main-content">
                <Outlet />
            </main>
        </div>
    );
}