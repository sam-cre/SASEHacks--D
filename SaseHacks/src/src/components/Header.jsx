// src/components/Header.jsx

function Header() {
    return (
        <header className="header-container">
            <h1>Pooop</h1>
            <p>Welcome to my site!</p>
            <nav>
                <ul>
                    <li><a href="#about">About</a></li>
                    <li><a href="#projects">Projects</a></li>
                    <li><a href="#contact">Contact me</a></li>
                </ul>
            </nav>
        </header>
    );
}

// Don't forget this! It's what allows App.jsx to import it.
export default Header;
