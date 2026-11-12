import { useState } from 'react';
import './TimeControl.css';

// A clock button that lets the user pick a date.
// `date` is the chosen date as "YYYY-MM-DD", or "" for today.
export default function TimeControl({ date, setDate }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="time-control">
      <button
        className={date ? 'clock-button active' : 'clock-button'}
        title="Show older news"
        onClick={() => setOpen(!open)}
      >
        🕓
      </button>

      {open && (
        <div className="time-panel">
          <p>Show news published before:</p>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <button onClick={() => setDate('')}>Today</button>
        </div>
      )}
    </div>
  );
}
