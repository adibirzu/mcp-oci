#!/bin/bash

echo "🔥 Testing Pyroscope Connection from Grafana"
echo "============================================="

# Test direct access to Pyroscope
echo -n "Testing Pyroscope from host... "
if curl -s --max-time 5 "http://localhost:4040/" >/dev/null; then
    echo "✅ SUCCESS"
else
    echo "❌ FAILED"
    exit 1
fi

# Test from Grafana container
echo -n "Testing Pyroscope from Grafana container... "
if docker exec grafana sh -c "wget -qO- http://pyroscope:4040/ --timeout=5" >/dev/null 2>&1; then
    echo "✅ SUCCESS"
else
    echo "❌ FAILED"
    exit 1
fi

# Test Pyroscope API
echo -n "Testing Pyroscope API... "
if response=$(curl -s "http://localhost:4040/api/v1/applications" 2>/dev/null); then
    if echo "$response" | jq . >/dev/null 2>&1; then
        echo "✅ SUCCESS (API responding)"
    else
        echo "✅ SUCCESS (responding, but may have no data yet)"
    fi
else
    echo "❌ FAILED"
fi

# Test Grafana data source
echo -n "Testing Grafana Pyroscope data source configuration... "
if ds_info=$(curl -s -u admin:admin "http://localhost:3000/api/datasources" | jq '.[] | select(.name == "Pyroscope")' 2>/dev/null); then
    if [ -n "$ds_info" ]; then
        echo "✅ SUCCESS (Data source configured)"
        echo "   URL: $(echo "$ds_info" | jq -r '.url')"
        echo "   Access: $(echo "$ds_info" | jq -r '.access')"
    else
        echo "❌ FAILED (Data source not found)"
    fi
else
    echo "❌ FAILED (Cannot access Grafana API)"
fi

echo
echo "🎉 Pyroscope connectivity test complete!"
echo "ℹ️  Note: The '[::1]:4040 connection refused' error should now be resolved."
echo "ℹ️  If you still see the error, restart Grafana: docker-compose restart grafana"