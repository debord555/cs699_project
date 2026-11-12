import { useEffect, useRef, useState } from 'react';
import './Sidebar.css';

// Article details we have already downloaded, by id. It lives outside the
// components so it survives map moves and nothing is fetched twice.
const cache = {};

export default function Sidebar({ ids, setHoveredId }) {
  const listRef = useRef(null);

  // The map moved or zoomed, so scroll the list back to the top
  useEffect(() => {
    listRef.current.scrollTop = 0;
  }, [ids]);

  return (
    <aside className="sidebar">
      <header className="sidebar-header">
        <h2>Articles</h2>
        <span className="sidebar-count">{ids.length}</span>
      </header>
      {ids.length === 0 && <p className="sidebar-empty">No articles in this area.</p>}
      <ul className="sidebar-list" ref={listRef}>
        {ids.map((id) => (
          <ArticleEntry key={id} id={id} listRef={listRef} setHoveredId={setHoveredId} />
        ))}
      </ul>
    </aside>
  );
}

function ArticleEntry({ id, listRef, setHoveredId }) {
  // undefined = not loaded yet, null = not found
  const [article, setArticle] = useState(cache[id]);
  const entryRef = useRef(null);

  // Fetch the details only once this entry scrolls into view
  useEffect(() => {
    if (article !== undefined) return;

    let loading = false;
    const observer = new IntersectionObserver(
      async ([entry]) => {
        if (!entry.isIntersecting || loading) return;
        loading = true;
        try {
          const res = await fetch(`/api/get_news?id=${id}`);
          const rows = await res.json();
          // Each row is [id, title, url, published_at, image_url]
          let details = null;
          if (rows.length > 0) {
            const [, title, url, publishedAt, imageUrl] = rows[0];
            details = { title, url, publishedAt, imageUrl };
          }
          cache[id] = details;
          setArticle(details);
        } catch {
          loading = false; // try again next time it scrolls into view
        }
      },
      // Start loading a little before the entry is actually visible
      { root: listRef.current, rootMargin: '200px 0px' },
    );
    observer.observe(entryRef.current);

    // Stop watching when the entry is removed or has loaded
    return () => observer.disconnect();
  }, [id, article, listRef]);

  if (article === undefined) {
    return (
      <li
        ref={entryRef}
        className="article article-loading"
        onMouseEnter={() => setHoveredId(id)}
        onMouseLeave={() => setHoveredId(null)}
      >
        Loading article #{id}…
      </li>
    );
  }
  if (article === null) {
    return <li className="article article-loading">Article #{id} not found</li>;
  }

  return (
    <li
      className="article"
      onMouseEnter={() => setHoveredId(id)}
      onMouseLeave={() => setHoveredId(null)}
    >
      <a href={article.url} target="_blank" rel="noopener noreferrer">
        {article.imageUrl && (
          <img className="article-image" src={article.imageUrl} alt="" loading="lazy" />
        )}
        <div className="article-text">
          <span className="article-title">{article.title}</span>
          {article.publishedAt && (
            <span className="article-date">{new Date(article.publishedAt).toLocaleString()}</span>
          )}
        </div>
      </a>
    </li>
  );
}
