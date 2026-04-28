import { useParams, useNavigate } from "react-router-dom";

function DetailsPage() {
  const { type } = useParams();
  const navigate = useNavigate();

  const data = {
    order: ["Order ID: RG12345",
        "Tracking ID: TRK987654",
        "Items: Medical Supplies",
        "Weight: 12kg",
        "Priority: High",
        "Packaging: Secure"],
    delivery: ["Status: In Transit",
        "ETA: 2 hours",
        "Current Location: NH44",
        "Speed: 60 km/h",
        "Stops Remaining: 2",
        "Live Tracking Enabled"],
    driver: ["Name: Ravi Kumar",
        "Phone: +91 9876543210",
        "Experience: 5 years",
        "Rating: 4.8 ⭐",
        "Vehicle: AP09 AB1234",
        "License: Verified"],
    sender: ["Location: Hyderabad Warehouse",
        "Contact: +91 9000000000",
        "Dispatch Time: 10:00 AM",
        "Handled By: Logistics Team"],
    receiver: ["Location: Bangalore Hospital",
        "Contact: +91 9888888888",
        "Receiving Time: Expected 4 PM",
        "Department: Emergency Care"],
    handling: ["Fragile Item",
        "This Side Up ↑",
        "Handle with care",
        "Avoid vibrations"],
    temperature: ["Maintained Temperature: 5°C",
        "Cooling System: Active",
        "Deviation: None",
        "Sensors: Working properly"],
    sustainability: [ "CO₂ Emission: 12kg",
        "Fuel Type: Diesel",
        "Eco Score: 78%",
        "Carbon-aware routing enabled"],
    tradeoff: ["Cost: Low",
        "Emission: Medium",
        "Optimized Route: Yes",
        "Balance Strategy: Active"]
  };

  return (
    <div style={{ padding: 20 }}>
      <button onClick={() => navigate("/")}>⬅ Back</button>
      <h2>{type.toUpperCase()} DETAILS</h2>
      {data[type]?.map((d, i) => <p key={i}>• {d}</p>)}
    </div>
  );
}

export default DetailsPage;