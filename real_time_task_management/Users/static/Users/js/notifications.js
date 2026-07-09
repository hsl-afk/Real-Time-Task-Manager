document.addEventListener("DOMContentLoaded", function() {
    const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const wsUrl = wsProtocol + window.location.host + "/ws/notifications/";
    
    const socket = new WebSocket(wsUrl);

    socket.onopen = function(e) {
        console.log("Connected to WebSockets for real-time notifications!");
    };

    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        console.log("REAL-TIME UPDATE RECEIVED:", data);
        alert("Real-Time Notification: " + data.message);
    };

    socket.onclose = function(e) {
        console.error("WebSocket closed unexpectedly");
    };
});
