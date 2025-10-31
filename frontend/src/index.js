import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

let container = document.getElementById('root');
if (!container) {
	// create root container if missing (prevents "Target container is not a DOM element" error)
	container = document.createElement('div');
	container.id = 'root';
	document.body.appendChild(container);
}

const root = createRoot(container);
root.render(<App />);
