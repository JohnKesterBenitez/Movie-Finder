const searchBtn = document.getElementById('search-btn');
const movieInput = document.getElementById('movie-input');
const resultContainer = document.getElementById('result-container');

// Palitan ito ng sarili mong OMDb API Key
const API_KEY = 'YOUR_API_KEY'; 

async function getMovieData() {
  const movieTitle = movieInput.value.trim();

  // Error state kung walang inilagay na input
  if (!movieTitle) {
    resultContainer.innerHTML = `<p class="error-msg">Paki-type ang pangalan ng pelikula.</p>`;
    return;
  }

  // Loading state habang naghihintay ng data
  resultContainer.innerHTML = `<p>Naghahanap...</p>`;

  try {
    const response = await fetch(`https://www.omdbapi.com/?t=${encodeURIComponent(movieTitle)}&apikey=${API_KEY}`);
    const data = await response.json();

    // Handling ng "Movie Not Found" mula sa API
    if (data.Response === "False") {
      resultContainer.innerHTML = `<p class="error-msg">Hindi nahanap ang pelikulang "${movieTitle}". Subukan ang ibang pamagat.</p>`;
      return;
    }

    // Dynamic Rendering ng Movie Card
    resultContainer.innerHTML = `
      <div class="movie-card">
        <img src="${data.Poster !== 'N/A' ? data.Poster : 'https://via.placeholder.com/200x300?text=No+Poster'}" alt="${data.Title}">
        <div class="movie-info">
          <h2>${data.Title}</h2>
          <p class="meta"><strong>Released:</strong> ${data.Year} | <strong>Rating:</strong> ⭐ ${data.imdbRating}</p>
          <p class="plot"><strong>Storyline:</strong> ${data.Plot}</p>
        </div>
      </div>
    `;

  } catch (error) {
    resultContainer.innerHTML = `<p class="error-msg">Nagkaroon ng problema sa koneksyon. Subukan ulit mamaya.</p>`;
  }
}

// Event Listeners para sa Button Click at Enter Key
searchBtn.addEventListener('click', getMovieData);
movieInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') getMovieData();
});