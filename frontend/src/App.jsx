import React from 'react';
import { useState, useRef } from 'react';
import { MapContainer, TileLayer, useMapEvents, CircleMarker, Popup } from 'react-leaflet';

// Critical: Leaflet tile styling will break without this import
import 'leaflet/dist/leaflet.css';

function NewsPins() {
  const [pins, setPins] = useState([]);
  const controller = useRef(null);

  const fetchPins = async (map) => {
    // Cancel the previous request so a slow, outdated response can't overwrite a newer one
    controller.current?.abort();
    controller.current = new AbortController();

    const b = map.getBounds();
    // At low zoom the bounds can extend past the valid lat/lon range
    const params = new URLSearchParams({
      lat_min: Math.max(b.getSouth(), -90),
      lon_min: Math.max(b.getWest(), -180),
      lat_max: Math.min(b.getNorth(), 90),
      lon_max: Math.min(b.getEast(), 180),
      zoom: map.getZoom(),
    });
    try {
      const res = await fetch(`/api/get_news_ids?${params}`, { signal: controller.current.signal });
      if (res.ok) setPins(await res.json());
    } catch (e) {
      if (e.name !== 'AbortError') throw e;
    }
  };

  const map = useMapEvents({
    moveend: () => fetchPins(map),
    load: () => fetchPins(map),
  });

  return pins.map(([id, lat, lon]) => (
    <CircleMarker
      key={`${id}-${lat}-${lon}`}
      center={[lat, lon]}
      radius={7}
      pathOptions={{ color: 'white', weight: 1, fillColor: '#cf00ff', fillOpacity: 1.0 }}
    >
      <Popup>Article #{id}</Popup>
    </CircleMarker>
  ));

}

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
        <NewsPins />
      </MapContainer>
    </div>
  );
}