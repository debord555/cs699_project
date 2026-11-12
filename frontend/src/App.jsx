import { useState, useRef, useEffect } from 'react';
import { MapContainer, TileLayer, useMapEvents, CircleMarker, Popup } from 'react-leaflet';
import Sidebar from './Sidebar';
import TimeControl from './TimeControl';

// Critical: Leaflet tile styling will break without this import
import 'leaflet/dist/leaflet.css';

// Returns the ids of the articles on screen, closest to the map center first.
// The backend returns some pins just outside the screen, so those are skipped.
function getVisibleIds(pins, map) {
  const bounds = map.getBounds();
  const center = map.getCenter();

  const onScreen = pins
    .filter(([, lat, lon]) => bounds.contains([lat, lon]))
    .map(([id, lat, lon]) => ({ id, distance: center.distanceTo([lat, lon]) }));
  onScreen.sort((a, b) => a.distance - b.distance);

  // An article can have several pins; a Set keeps only its first (closest) one
  return [...new Set(onScreen.map((pin) => pin.id))];
}

function NewsPins({ pins, date, onPinsLoaded }) {
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
    // Only show news from before the chosen date (if one is chosen)
    if (date) {
      params.set('before', date + 'T00:00:00Z');
    }
    try {
      const res = await fetch(`/api/get_news_ids?${params}`, { signal: controller.current.signal });
      if (res.ok) {
        const newPins = await res.json();
        onPinsLoaded(newPins, getVisibleIds(newPins, map));
      }
    } catch (e) {
      if (e.name !== 'AbortError') throw e;
    }
  };

  const map = useMapEvents({
    moveend: () => fetchPins(map),
    load: () => fetchPins(map),
  });

  // Load the pins again whenever the chosen date changes
  useEffect(() => {
    fetchPins(map);
  }, [date]);

  // Each pin is [article id, lat, lon, location id]. An article can have two
  // locations at the same spot, so the key uses the location id to stay unique.
  return pins.map(([id, lat, lon, locationId]) => (
    <CircleMarker
      key={`${id}-${locationId}`}
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

  const [pins, setPins] = useState([]);
  const [visibleIds, setVisibleIds] = useState([]);
  // The chosen date as "YYYY-MM-DD", or "" for today
  const [date, setDate] = useState('');

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex' }}>
      <div style={{ flex: 1, minWidth: 0, height: '100%', position: 'relative' }}>
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
          <NewsPins
            pins={pins}
            date={date}
            onPinsLoaded={(newPins, ids) => {
              setPins(newPins);
              setVisibleIds(ids);
            }}
          />
        </MapContainer>
        <TimeControl date={date} setDate={setDate} />
      </div>
      <Sidebar ids={visibleIds} />
    </div>
  );
}
