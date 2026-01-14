const currentUsername = window.CURRENT_USERNAME;
let currentThreadId = null;
let currentRecipient = null;
let messageInterval = null;
const openedThreads = new Set();
const params = new URLSearchParams(window.location.search);
const preselectedUser = params.get('user');

async function loadChatThreads() {
    try {
        const res = await fetch('/api/chat_threads');
        if (!res.ok) return;

        const threads = await res.json();
        const container = document.getElementById('friends-container');
        container.innerHTML = '';

        if (threads.length === 0) {
            container.innerHTML = '<p>No chats yet.</p>';
            return;
        }

        threads.forEach(thread => {
            const div = document.createElement('div');
            div.className = 'friend-item';
            div.textContent = thread.other_user;
            div.onclick = () => startChat(thread.other_user);
            container.appendChild(div);
        });
    } catch (err) {
        console.error(err);
    }
}

async function startChat(recipient) {
    if (!recipient) return;

    currentRecipient = recipient;
    document.getElementById('chat-with').textContent = `Chat with ${recipient}`;
    document.getElementById('message-input-container').style.display = 'block';

    try {
        const res = await fetch('/api/chat_threads');
        if (!res.ok) return;

        const threads = await res.json();
        const thread = threads.find(t => t.other_user === recipient);

        if (thread) {
            currentThreadId = thread.id;
            openedThreads.add(thread.id);
            await loadMessages(thread.id);
        } else {
            currentThreadId = null;
            document.getElementById('messages-container').innerHTML =
                '<p>Start a conversation!</p>';
        }

        // Refresh sidebar once to highlight active chat
        loadChatThreads();

        if (messageInterval) clearInterval(messageInterval);

        // Poll for updates (messages + sidebar)
        messageInterval = setInterval(async () => {
            if (currentThreadId) {
                await loadMessages(currentThreadId);
            }
            loadChatThreads();
        }, 2000);

    } catch (err) {
        console.error(err);
    }
}


async function loadMessages(threadId) {
    try {
        const res = await fetch(`/api/messages/${threadId}`);
        if (!res.ok) return;

        const messages = await res.json();
        const container = document.getElementById('messages-container');
        container.innerHTML = '';

        if (messages.length === 0) {
            container.innerHTML = '<p>No messages yet.</p>';
            return;
        }

        messages.forEach(msg => {
            const div = document.createElement('div');
            div.className = `message ${msg.sender === currentUsername ? 'sent' : 'received'}`;
            div.innerHTML = `
                <strong>${msg.sender}:</strong> ${msg.message}
                <small>${new Date(msg.time).toLocaleString()}</small>
            `;
            container.appendChild(div);
        });

        container.scrollTop = container.scrollHeight;
    } catch (err) {
        console.error(err);
    }
}

document.getElementById('message-form')?.addEventListener('submit', async e => {
    e.preventDefault();

    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message || !currentRecipient) return;

    input.value = '';

    // Send message
    await fetch('/api/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient: currentRecipient, message })
    });

    // 🔑 If thread doesn't exist yet, discover it
    if (!currentThreadId) {
        const res = await fetch('/api/chat_threads');
        const threads = await res.json();
        const thread = threads.find(t => t.other_user === currentRecipient);

        if (thread) {
            currentThreadId = thread.id;
            openedThreads.add(thread.id);
        }
    }

    // 🔑 Always load messages once thread ID is known
    if (currentThreadId) {
        await loadMessages(currentThreadId);
    }

    // Refresh sidebar so chat appears immediately
    loadChatThreads();
});


/* Chat init */
if (currentUsername && document.getElementById('friends-container')) {
    loadChatThreads().then(() => {
        if (preselectedUser) {
            startChat(preselectedUser);
        }
    });
}

