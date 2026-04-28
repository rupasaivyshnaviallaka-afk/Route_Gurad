import React, { useState, useEffect } from "react";
import {
  GoogleMap,
  useJsApiLoader,
  TrafficLayer,
  Marker,
  Polyline
} from "@react-google-maps/api";
import { useNavigate } from "react-router-dom";

function MapComponent() {
  const navigate = useNavigate();

  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: "AIzaSyD_Vx4__PDg0ToTicOM5Z8e-L6b_ElkPLY"
  });

  // State variables
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [path, setPath] = useState([]);
  const [position, setPosition] = useState(null);
  const [routeColor, setRouteColor] = useState("blue");
  const [status, setStatus] = useState("No updates yet");
  const [weather, setWeather] = useState("sunny");
  const [trafficInfo, setTrafficInfo] = useState("No traffic data");
  
  // ML Mode
  const [useML, setUseML] = useState(true);
  const [delayRisk, setDelayRisk] = useState(null);
  const [predictedETA, setPredictedETA] = useState(null);
  const [mlRecommendation, setMlRecommendation] = useState("");
  
  // Vehicle type for fuel prediction
  const [vehicleType, setVehicleType] = useState("truck");
  const [loadWeight, setLoadWeight] = useState(5000);
  const [fuelData, setFuelData] = useState(null);
  const [showFuelPanel, setShowFuelPanel] = useState(false);
  
  // Risk Score
  const [riskData, setRiskData] = useState(null);

  // ROUTE CALCULATION
  const calculateRoute = async () => {
    if (!origin || !destination) {
      alert("Please enter both source and destination");
      return;
    }
    
    if (!window.google) {
      alert("Google Maps not loaded yet. Please wait.");
      return;
    }

    try {
      const directionsService = new window.google.maps.DirectionsService();
      
      const request = {
        origin: origin,
        destination: destination,
        travelMode: window.google.maps.TravelMode.DRIVING
      };
      
      const result = await directionsService.route(request);
      
      const routePath = result.routes[0].overview_path.map((point) => ({
        lat: point.lat(),
        lng: point.lng()
      }));
      
      setPath(routePath);
      setPosition(routePath[0]);
      setStatus("Route created ✅");
      
      if (useML && routePath.length > 0) {
        await getMLAnalysis(routePath.length);
      }
      
    } catch (error) {
      console.error("Route error:", error);
      alert("Could not find route. Please check your locations.\nUse format: City, Country (e.g., Mumbai, India)");
    }
  };

  // ML Analysis
  const getMLAnalysis = async (distance) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/ml/analyze?distance=${distance}&weather=${weather}`
      );
      
      if (!res.ok) throw new Error("ML API error");
      
      const data = await res.json();
      
      setRouteColor(data.color);
      setStatus(data.message);
      
      if (data.detailed_analysis) {
        const analysis = data.detailed_analysis;
        if (analysis.traffic_prediction) {
          setTrafficInfo(analysis.traffic_prediction.description);
        }
        if (analysis.delay_prediction) {
          setDelayRisk(analysis.delay_prediction);
        }
        if (analysis.eta_prediction) {
          setPredictedETA(analysis.eta_prediction);
        }
        if (analysis.recommendation) {
          setMlRecommendation(analysis.recommendation);
        }
      } else {
        if (data.color === "red") setTrafficInfo("Heavy traffic 🔴");
        else if (data.color === "yellow") setTrafficInfo("Moderate traffic 🟡");
        else setTrafficInfo("Clear road 🟢");
      }
      
    } catch (error) {
      console.error("ML API error:", error);
      await getRuleBasedSuggestion(distance);
    }
  };

  // Rule-based fallback
  const getRuleBasedSuggestion = async (distance) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/predict?distance=${distance}&weather=${weather}`
      );
      const data = await res.json();
      setRouteColor(data.color);
      setStatus(data.message);
      if (data.color === "red") setTrafficInfo("Heavy traffic 🔴");
      else if (data.color === "yellow") setTrafficInfo("Moderate traffic 🟡");
      else setTrafficInfo("Clear road 🟢");
    } catch (error) {
      console.error("API error:", error);
      setStatus("Backend not connected. Using local calculation.");
    }
  };

  // AI Suggestion
  const getSmartRoute = async () => {
    if (path.length === 0) {
      alert("Click Start Route first!");
      return;
    }
    
    const distance = path.length;
    
    if (useML) {
      await getMLAnalysis(distance);
    } else {
      await getRuleBasedSuggestion(distance);
    }
  };

  // Fuel prediction
  const predictFuel = async () => {
    if (path.length === 0) {
      alert("Calculate route first!");
      return;
    }
    
    let trafficLevel = "moderate";
    if (routeColor === "red") trafficLevel = "heavy";
    else if (routeColor === "green") trafficLevel = "light";
    
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/fuel/predict?distance_km=${path.length}&traffic_level=${trafficLevel}&vehicle_type=${vehicleType}&load_weight_kg=${loadWeight}`
      );
      const data = await res.json();
      setFuelData(data);
    } catch (error) {
      console.error("Fuel prediction error:", error);
      alert("Could not fetch fuel prediction");
    }
  };

  // Risk Score
  const fetchRiskScore = async () => {
    if (path.length === 0) {
      alert("Please calculate a route first!");
      return;
    }
    
    try {
      const res = await fetch('http://127.0.0.1:8000/ml/risk-score?route_id=123');
      const data = await res.json();
      setRiskData(data);
    } catch (error) {
      console.error("Risk score error:", error);
      alert("Could not fetch risk score. Make sure backend is running.");
    }
  };

  // Toggle ML mode
  const toggleML = () => {
    setUseML(!useML);
    setStatus(`Switched to ${!useML ? "ML" : "Rule-based"} mode`);
    setDelayRisk(null);
    setPredictedETA(null);
    setMlRecommendation("");
  };

  // VEHICLE ANIMATION
  useEffect(() => {
    if (path.length === 0) return;

    let i = 0;
    const interval = setInterval(() => {
      if (i < path.length) {
        setPosition(path[i]);
        i++;
      }
    }, 200);

    return () => clearInterval(interval);
  }, [path]);

  if (!isLoaded) return <h2>Loading Map...</h2>;

  return (
    <div style={{ fontFamily: "Segoe UI", background: "#f4f6fb", minHeight: "100vh", padding: "20px" }}>

      {/* HEADER */}
      <h2 style={{ textAlign: "center", marginBottom: "20px" }}>
        🚚 RouteGuard Smart Dashboard
        {useML && <span style={{ fontSize: "14px", background: "#22c55e", color: "white", padding: "4px 8px", borderRadius: "20px", marginLeft: "10px" }}>🤖 ML Enhanced</span>}
      </h2>

      {/* ML Mode Toggle */}
      <div style={{ textAlign: "center", marginBottom: "15px" }}>
        <button
          onClick={toggleML}
          style={{
            padding: "8px 16px",
            background: useML ? "#ef4444" : "#22c55e",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer"
          }}
        >
          {useML ? "🔴 Switch to Rule-based" : "🟢 Switch to ML Mode"}
        </button>
      </div>

      {/* DASHBOARD CARDS */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px,1fr))",
        gap: "15px",
        marginBottom: "30px"
      }}>
        {[
          { name: "Order", icon: "🧾", color: "#10b981", path: "order" },
          { name: "Delivery", icon: "🚚", color: "#3b82f6", path: "delivery" },
          { name: "Driver", icon: "👤", color: "#f59e0b", path: "driver" },
          { name: "Sender", icon: "📍", color: "#6366f1", path: "sender" },
          { name: "Receiver", icon: "📍", color: "#ec4899", path: "receiver" },
          { name: "Handling", icon: "⚠️", color: "#ef4444", path: "handling" },
          { name: "Temperature", icon: "🌡️", color: "#06b6d4", path: "temperature" },
          { name: "Sustainability", icon: "🌱", color: "#22c55e", path: "sustainability" },
          { name: "Trade-off", icon: "⚖️", color: "#a855f7", path: "tradeoff" }
        ].map((item, i) => (
          <div
            key={i}
            onClick={() => navigate(`/details/${item.path}`)}
            style={{
              background: "white",
              padding: "20px",
              borderRadius: "12px",
              boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
              cursor: "pointer",
              textAlign: "center",
              borderTop: `4px solid ${item.color}`,
              transition: "0.3s"
            }}
            onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-5px)"}
            onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}
          >
            <div style={{ fontSize: "28px" }}>{item.icon}</div>
            <h4>{item.name}</h4>
          </div>
        ))}
      </div>

      {/* SEARCH BOXES */}
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "12px",
        marginBottom: "20px"
      }}>
        <input
          placeholder="Enter Source Location (e.g., Mumbai, India)"
          onChange={(e) => setOrigin(e.target.value)}
          style={{ width: "300px", padding: "12px", borderRadius: "8px", border: "1px solid #ccc" }}
        />

        <input
          placeholder="Enter Destination Location (e.g., Pune, India)"
          onChange={(e) => setDestination(e.target.value)}
          style={{ width: "300px", padding: "12px", borderRadius: "8px", border: "1px solid #ccc" }}
        />

        <select
          onChange={(e) => setWeather(e.target.value)}
          style={{ width: "320px", padding: "12px", borderRadius: "8px" }}
        >
          <option value="sunny">☀️ Sunny</option>
          <option value="moderate">🌥️ Moderate</option>
          <option value="rainy">🌧️ Rainy</option>
        </select>

        <select
          onChange={(e) => setVehicleType(e.target.value)}
          style={{ width: "320px", padding: "12px", borderRadius: "8px" }}
          value={vehicleType}
        >
          <option value="truck">🚛 Truck</option>
          <option value="van">🚐 Van</option>
          <option value="car">🚗 Car</option>
        </select>

        <input
          type="number"
          placeholder="Load Weight (kg)"
          onChange={(e) => setLoadWeight(Number(e.target.value))}
          style={{ width: "300px", padding: "12px", borderRadius: "8px", border: "1px solid #ccc" }}
          value={loadWeight}
        />

        {/* BUTTONS */}
        <div style={{ display: "flex", gap: "15px", marginTop: "10px", flexWrap: "wrap", justifyContent: "center" }}>
          <button
            onClick={calculateRoute}
            style={{
              padding: "12px 20px",
              fontSize: "16px",
              background: "#2563eb",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer"
            }}
          >
            🚀 Start Route
          </button>

          <button
            onClick={getSmartRoute}
            style={{
              padding: "12px 20px",
              fontSize: "16px",
              background: "#16a34a",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer"
            }}
          >
            {useML ? "🤖 ML Analysis" : "📏 Rule-based Suggestion"}
          </button>

          <button
            onClick={() => setShowFuelPanel(!showFuelPanel)}
            style={{
              padding: "12px 20px",
              fontSize: "16px",
              background: "#f59e0b",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer"
            }}
          >
            ⛽ Fuel Calculator
          </button>

          <button
            onClick={fetchRiskScore}
            style={{
              padding: "12px 20px",
              fontSize: "16px",
              background: "#ef4444",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer"
            }}
          >
            📊 Risk Score
          </button>
        </div>
      </div>

      {/* ML DETAILS PANEL */}
      {useML && delayRisk && (
        <div style={{
          background: "white",
          padding: "15px",
          borderRadius: "12px",
          marginBottom: "15px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
        }}>
          <h4 style={{ margin: "0 0 10px 0" }}>🤖 ML Predictions</h4>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px,1fr))", gap: "10px" }}>
            <div>
              <strong>Delay Risk:</strong>
              <span style={{
                display: "inline-block",
                marginLeft: "8px",
                padding: "2px 8px",
                borderRadius: "12px",
                background: delayRisk.risk_level === "HIGH" ? "#ef4444" : delayRisk.risk_level === "MEDIUM" ? "#f59e0b" : "#22c55e",
                color: "white"
              }}>
                {delayRisk.risk_level} ({Math.round(delayRisk.delay_probability * 100)}%)
              </span>
            </div>
            {predictedETA && (
              <div>
                <strong>⏱️ Predicted ETA:</strong> {predictedETA.formatted}
              </div>
            )}
            <div>
              <strong>🚦 Traffic:</strong> {trafficInfo}
            </div>
          </div>
          {mlRecommendation && (
            <div style={{ marginTop: "10px", padding: "8px", background: "#fef3c7", borderRadius: "8px" }}>
              💡 <strong>Recommendation:</strong> {mlRecommendation}
            </div>
          )}
        </div>
      )}

      {/* FUEL CALCULATOR PANEL */}
      {showFuelPanel && (
        <div style={{
          background: "white",
          padding: "15px",
          borderRadius: "12px",
          marginBottom: "15px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
        }}>
          <h4 style={{ margin: "0 0 10px 0" }}>⛽ Fuel Consumption Calculator</h4>
          <button
            onClick={predictFuel}
            style={{
              padding: "8px 16px",
              background: "#f59e0b",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              marginBottom: "10px"
            }}
          >
            Calculate Fuel for Current Route
          </button>
          {fuelData && (
            <div style={{ fontSize: "14px" }}>
              <div>📊 <strong>Fuel:</strong> {fuelData.predicted_fuel_liters} liters</div>
              <div>💰 <strong>Cost:</strong> ${fuelData.cost_estimate_usd}</div>
              <div>🌍 <strong>CO2:</strong> {fuelData.predicted_co2_kg} kg</div>
              {fuelData.recommendations && fuelData.recommendations.map((tip, idx) => (
                <div key={idx}>💡 {tip}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* RISK SCORE DISPLAY */}
      {riskData && (
        <div style={{
          background: "white",
          padding: "15px",
          borderRadius: "12px",
          marginBottom: "15px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          borderLeft: `4px solid ${riskData.risk_level === "CRITICAL" ? "#ef4444" : 
                         riskData.risk_level === "HIGH" ? "#f59e0b" : 
                         riskData.risk_level === "MEDIUM" ? "#eab308" : "#22c55e"}`
        }}>
          <h4 style={{ margin: "0 0 10px 0" }}>📊 Supply Chain Risk Assessment</h4>
          
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <span>Overall Risk Score:</span>
            <span style={{
              fontSize: "24px",
              fontWeight: "bold",
              color: riskData.risk_level === "CRITICAL" ? "#ef4444" : 
                     riskData.risk_level === "HIGH" ? "#f59e0b" : 
                     riskData.risk_level === "MEDIUM" ? "#eab308" : "#22c55e"
            }}>
              {riskData.overall_risk_score}%
            </span>
          </div>
          
          <div style={{ marginBottom: "10px" }}>
            <strong>Risk Level:</strong> 
            <span style={{
              marginLeft: "8px",
              padding: "2px 8px",
              borderRadius: "12px",
              background: riskData.risk_level === "CRITICAL" ? "#ef4444" : 
                         riskData.risk_level === "HIGH" ? "#f59e0b" : 
                         riskData.risk_level === "MEDIUM" ? "#eab308" : "#22c55e",
              color: "white"
            }}>
              {riskData.risk_level}
            </span>
          </div>
          
          <div style={{ marginBottom: "10px" }}>
            <strong>Recommended Action:</strong> {riskData.recommended_action}
          </div>
          
          <details style={{ marginTop: "10px", cursor: "pointer" }}>
            <summary>View Risk Breakdown</summary>
            <div style={{ marginTop: "10px", fontSize: "13px" }}>
              {riskData.risk_breakdown && Object.entries(riskData.risk_breakdown).map(([key, value]) => (
                <div key={key} style={{ marginBottom: "5px" }}>
                  {key.replace(/_/g, " ").toUpperCase()}: 
                  <div style={{
                    display: "inline-block",
                    marginLeft: "10px",
                    width: "100px",
                    height: "8px",
                    background: "#e5e7eb",
                    borderRadius: "4px",
                    overflow: "hidden"
                  }}>
                    <div style={{
                      width: `${value}%`,
                      height: "100%",
                      background: value > 60 ? "#ef4444" : value > 30 ? "#f59e0b" : "#22c55e"
                    }}></div>
                  </div>
                  <span style={{ marginLeft: "8px" }}>{value}%</span>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}

      {/* STATUS */}
      <div style={{ textAlign: "center", marginBottom: "10px" }}>
        <h3>{status}</h3>
        <p>🚗 Traffic: {trafficInfo}</p>
        <p>🌦 Weather: {weather}</p>
        {useML && <p>🧠 Mode: ML-powered analysis</p>}
      </div>

      {/* MAP */}
      <GoogleMap
        mapContainerStyle={{
          width: "100%",
          height: "500px",
          borderRadius: "12px"
        }}
        center={{ lat: 17.385, lng: 78.4867 }}
        zoom={6}
      >
        <TrafficLayer />

        {path.length > 0 && (
          <Polyline
            path={path}
            options={{ strokeColor: routeColor, strokeWeight: 5 }}
          />
        )}

        {position && <Marker position={position} />}
      </GoogleMap>

    </div>
  );
}

export default MapComponent;