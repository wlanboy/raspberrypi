let page = 1;
let query = "";
let loading = false;
let hasMore = true;

const grid = document.getElementById('notes-grid');
const searchInput = document.getElementById('search');

async function loadNotes(reset = false) {
    if (loading || (!hasMore && !reset)) return;
    
    loading = true;
    if (reset) {
        page = 1;
        grid.innerHTML = '';
        hasMore = true;
        window.scrollTo(0, 0);
    }
    
    document.getElementById('loader').style.display = 'block';
    
    try {
        const response = await fetch(`/api/notes?q=${encodeURIComponent(query)}&page=${page}`);
        const data = await response.json();
        
        if (data.length < 20) hasMore = false;
        
        data.forEach(note => {
            const card = document.createElement('div');
            card.className = 'card';
            const tagsHtml = note.tags.map(t => `<span class="tag">#${t}</span>`).join('');
            
            card.innerHTML = `
                <div class="date">${note.date_str}</div>
                <h2>${note.title}</h2>
                <div class="preview">${note.preview}</div>
                <div class="tags-container">${tagsHtml}</div>
            `;
            grid.appendChild(card);
        });
        
        page++;
    } catch (err) {
        console.error("Fehler beim Laden:", err);
    } finally {
        loading = false;
        document.getElementById('loader').style.display = 'none';
    }
}

// Debounce Funktion für performante Suche
let timeout = null;
searchInput.addEventListener('input', () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
        query = searchInput.value;
        loadNotes(true);
    }, 300);
});

// Infinite Scroll
window.addEventListener('scroll', () => {
    if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 800) {
        loadNotes();
    }
});

const modal = document.getElementById('note-modal');
const modalBody = document.getElementById('modal-body');
const closeBtn = document.querySelector('.close-button');
let currentRawContent = ""; // Zwischenspeicher für den reinen Text

function openNote(note) {
    // Nutzt marked.js um das Markdown zu rendern
    // Optionen setzen: 'breaks: true' wandelt \n in <br> um
    marked.setOptions({
        breaks: true,
        gfm: true
    });
    currentRawContent = note.full_content;

    modalBody.innerHTML = marked.parse(note.full_content);
    modal.style.display = "block";
    document.body.style.overflow = "hidden"; // Scrollen im Hintergrund verhindern
}

closeBtn.onclick = () => {
    modal.style.display = "none";
    document.body.style.overflow = "auto";
};

window.onclick = (event) => {
    if (event.target == modal) closeBtn.onclick();
};

async function loadNotes(reset = false) {
    if (loading || (!hasMore && !reset)) return;
    loading = true;
    if (reset) { page = 1; grid.innerHTML = ''; hasMore = true; }
    
    const response = await fetch(`/api/notes?q=${encodeURIComponent(query)}&page=${page}`);
    const data = await response.json();
    
    data.forEach(note => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class="date">${note.date_str}</div>
            <h2>${note.title}</h2>
            <div class="preview">${note.preview}</div>
            <div class="tags-container">${note.tags.map(t => `<span class="tag">#${t}</span>`).join('')}</div>
        `;
        
        // Klick-Event für das Modal
        card.onclick = () => openNote(note);
        
        grid.appendChild(card);
    });
    
    loading = false;
    page++;
}

const copyBtn = document.getElementById('copy-btn');
// Die Kopier-Logik
copyBtn.onclick = () => {
    const textToCopy = currentRawContent;

    // Versuche erst die moderne API
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).then(showSuccess).catch(err => console.error(err));
    } else {
        // Fallback für HTTP (unsichere Verbindung)
        const textArea = document.createElement("textarea");
        textArea.value = textToCopy;
        
        // Verstecke die Textarea außerhalb des Sichtfelds
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.top = "0";
        document.body.appendChild(textArea);
        
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            showSuccess();
        } catch (err) {
            console.error('Fallback-Kopieren fehlgeschlagen', err);
        }
        
        document.body.removeChild(textArea);
    }
};

// Hilfsfunktion für das visuelle Feedback
function showSuccess() {
    const originalText = copyBtn.innerText;
    copyBtn.innerText = "Kopiert! ✓";
    copyBtn.classList.add('success');
    
    setTimeout(() => {
        copyBtn.innerText = originalText;
        copyBtn.classList.remove('success');
    }, 2000);
}

// Initialer Aufruf
loadNotes();