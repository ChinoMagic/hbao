// static/js/script.js

document.addEventListener('DOMContentLoaded', function () {
    console.log('JavaScript đã được tải!');

    const role = window.role || null;  // role được truyền từ HTML
    const username = window.username || null;
    let selectedUser = null;

    if (role === 'admin') {
        const userItems = document.querySelectorAll('.user-item');
        const chatOutput = document.getElementById('chat-output');
        const errorMessage = document.getElementById('error-message');
        const chatTitle = document.getElementById('chat-title') || document.querySelector('h2');

        userItems.forEach(item => {
            item.addEventListener('click', () => {
                selectedUser = item.getAttribute('data-username');

                // Xóa nội dung chat cũ và thông báo lỗi
                chatOutput.innerHTML = '';
                if (errorMessage) errorMessage.textContent = '';

                // Cập nhật tiêu đề
                if (chatTitle) chatTitle.textContent = `Chat với ${selectedUser}`;

                // Tô sáng user đang chọn
                userItems.forEach(el => el.classList.remove('active'));
                item.classList.add('active');

                // Emit sự kiện tham gia phòng tương ứng (nếu muốn gọi từ client)
                if (window.socket && typeof window.socket.emit === 'function') {
                    if (window.currentRoom) {
                        window.socket.emit('leave', { room: window.currentRoom });
                    }
                    const newRoom = 'chat:' + selectedUser;
                    window.socket.emit('join', { room: newRoom });
                    window.currentRoom = newRoom;
                }
            });
        });
    }
});
