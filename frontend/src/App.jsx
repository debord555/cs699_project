import React from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';

// Critical: Leaflet tile styling will break without this import
import 'leaflet/dist/leaflet.css';

export default function App() {
  // Center roughly over the globe with a low zoom level
  const defaultCenter = [20, 0];
  const defaultZoom = 2;

  return (
    <div style={{ height: '100vh', width: '100vw' }}>
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        minZoom={2}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
      >
        {/* Base map tile layer from OpenStreetMap */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
      </MapContainer>
    </div>
  );
}