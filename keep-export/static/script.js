let page = 1;
let query = "";
let loading = false;
let hasMore = true;

const grid = document.getElementById('notes-grid');
const searchInput = document.getElementById('search');

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

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
            const tagsHtml = note.tags.map(t => `<span class="tag">#${escapeHtml(t)}</span>`).join('');

            card.innerHTML = `
                <div class="date">${escapeHtml(note.date_str)}</div>
                <h2>${escapeHtml(note.title)}</h2>
                <div class="preview">${escapeHtml(note.preview)}</div>
                <div class="tags-container">${tagsHtml}</div>
            `;
            card.onclick = () => openNote(note);
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

// Debounce für Suche
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
let currentRawContent = "";

function openNote(note) {
    marked.setOptions({ breaks: true, gfm: true });
    currentRawContent = note.full_content;
    modalBody.innerHTML = marked.parse(note.full_content);
    modal.style.display = "block";
    document.body.style.overflow = "hidden";
}

closeBtn.onclick = () => {
    modal.style.display = "none";
    document.body.style.overflow = "auto";
};

window.onclick = (event) => {
    if (event.target == modal) closeBtn.onclick();
};

const copyBtn = document.getElementById('copy-btn');
copyBtn.onclick = () => {
    const textToCopy = currentRawContent;
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).then(showSuccess).catch(err => console.error(err));
    } else {
        const textArea = document.createElement("textarea");
        textArea.value = textToCopy;
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

function showSuccess() {
    const originalText = copyBtn.innerText;
    copyBtn.innerText = "Kopiert! ✓";
    copyBtn.classList.add('success');
    setTimeout(() => {
        copyBtn.innerText = originalText;
        copyBtn.classList.remove('success');
    }, 2000);
}

loadNotes();
