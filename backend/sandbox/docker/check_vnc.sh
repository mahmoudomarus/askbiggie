#!/bin/bash

echo "=== VNC Service Check ==="
echo "Date: $(date)"
echo ""

echo "1. Checking X Display Server..."
if pgrep -f "Xvfb :99" > /dev/null; then
    echo "✅ Xvfb is running"
    ps aux | grep "Xvfb :99" | grep -v grep
else
    echo "❌ Xvfb not running"
fi
echo ""

echo "2. Checking VNC Password Setup..."
if [ -f ~/.vnc/passwd ]; then
    echo "✅ VNC password file exists"
    ls -la ~/.vnc/passwd
else
    echo "❌ VNC password file missing"
fi
echo ""

echo "3. Checking X11VNC Server..."
if pgrep -f "x11vnc" > /dev/null; then
    echo "✅ x11vnc is running"
    ps aux | grep "x11vnc" | grep -v grep
    echo "VNC port 5901 status:"
    netstat -ln | grep ":5901" || echo "Port 5901 not listening"
else
    echo "❌ x11vnc not running"
fi
echo ""

echo "4. Checking noVNC Proxy..."
if pgrep -f "novnc_proxy" > /dev/null; then
    echo "✅ noVNC proxy is running"
    ps aux | grep "novnc_proxy" | grep -v grep
    echo "noVNC port 6080 status:"
    netstat -ln | grep ":6080" || echo "Port 6080 not listening"
else
    echo "❌ noVNC proxy not running"
fi
echo ""

echo "5. Testing VNC Connection..."
if nc -z localhost 5901; then
    echo "✅ VNC port 5901 is reachable"
else
    echo "❌ VNC port 5901 is not reachable"
fi

if nc -z localhost 6080; then
    echo "✅ noVNC port 6080 is reachable"
else
    echo "❌ noVNC port 6080 is not reachable"
fi
echo ""

echo "6. Testing noVNC Web Interface..."
if curl -s -f "http://localhost:6080/vnc_lite.html" > /dev/null; then
    echo "✅ vnc_lite.html is accessible"
else
    echo "❌ vnc_lite.html is not accessible"
    echo "HTTP response:"
    curl -I "http://localhost:6080/vnc_lite.html" 2>/dev/null || echo "Connection failed"
fi
echo ""

echo "7. Supervisord Status..."
supervisorctl status
echo ""

echo "=== End VNC Check ===" 