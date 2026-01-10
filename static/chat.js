const currentUsername = '{{ username }}';
let currentThreadId = null;
let currentRecipient = null;
let messageInterval = null;

async function loadFriends() {
    try {
        const response = await fetch('/api/friends');
        if (!response.ok) {
            if (response.status === 401) {
                document.getElementById('friends-container').innerHTML =
                    '<p>Please log in to view friends.</p>';
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const friends = await response.json();
        const container = document.getElementById('friends-container');
        container.innerHTML = '';

        if (friends.length === 0) {
            container.innerHTML = '<p>No other users found.</p>';
            return;
        }

        friends.forEach(friend => {
            const div = document.createElement('div');
            div.className = 'friend-item';
            div.textContent = friend;
            div.onclick = () => startChat(friend);
            container.appendChild(div);
        });
    } catch (err) {
        console.error(err);
    }
}

async function loadChatThreads() {
    try {
        const [friendsRes, threadsRes] = await Promise.all([
            fetch('/api/friends'),
            fetch('/api/chat_threads')
        ]);

        if (!friendsRes.ok || !threadsRes.ok) return;

        const friends = await friendsRes.json();
        const threads = await threadsRes.json();
        const usersWithChats = new Set(threads.map(t => t.other_user));

        const container = document.getElementById('friends-container');
        container.innerHTML = '';

        friends.forEach(friend => {
            const div = document.createElement('div');
            div.className = `friend-item ${usersWithChats.has(friend) ? 'has-chat' : ''}`;
            div.textContent = friend;
            div.onclick = () => startChat(friend);
            container.appendChild(div);
        });
    } catch (err) {
        console.error(err);
    }
}

async function startChat(recipient) {
    currentRecipient = recipient;
    document.getElementById('chat-with').textContent = `Chat with ${recipient}`;
    document.getElementById('message-input-container').style.display = 'block';

    try {
        const res = await fetch('/api/chat_threads');
        const threads = await res.json();
        const thread = threads.find(t => t.other_user === recipient);

        if (thread) {
            currentThreadId = thread.id;
            await loadMessages(thread.id);
        } else {
            document.getElementById('messages-container').innerHTML =
                '<p>Start a conversation!</p>';
            currentThreadId = null;
        }

        if (messageInterval) clearInterval(messageInterval);

        messageInterval = setInterval(async () => {
            const res = await fetch('/api/chat_threads');
            const threads = await res.json();
            const thread = threads.find(t => t.other_user === currentRecipient);

            if (thread) {
                currentThreadId = thread.id;
                await loadMessages(thread.id);
            }
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
    if (!message) return;

    input.value = '';

    await fetch('/api/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient: currentRecipient, message })
    });
});

/* Chat init */
if (currentUsername && document.getElementById('friends-container')) {
    loadChatThreads();
}
