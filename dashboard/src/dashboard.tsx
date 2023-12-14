import { useState, useEffect } from "react";
import {
  GoogleMap,
  LoadScript,
  MarkerF,
  InfoWindowF,
} from "@react-google-maps/api";
import dotUrl from "./assets/dot.png";
import { Grid, Header, Segment } from "semantic-ui-react";

const remove_button_css = `
.gm-style-iw {
  text-align: center;
}
.gm-style-iw > button {
  display: none !important;
}`;

export default function Dashboard() {
  const [markers, setMarkers] = useState([
    {
      id: 1,
      position: { lat: 37.7749, lng: -122.4194 },
      content: "Marker 1 Info",
    },
    {
      id: 2,
      position: { lat: 37.7749, lng: -122.4294 },
      content: "Marker 2 Info",
    },
    // Add more markers as needed
  ]);
  const defaultCenter = { lat: 1.3521, lng: 103.8198 };
  const handleMarkerClick = (marker: object) => {
    setSelectedMarker(marker);
  };

  // Handle info window close event
  const handleInfoWindowClose = () => {
    setSelectedMarker(null);
  };

  const [selectedMarker, setSelectedMarker] = useState<any>(null);

  // useEffect(() => {
  //   handleMarkerClick(markers[0]);
  // }, [markers]);

  return (
    <Grid style={{ height: "100%", width: "100%" }}>
      {/* Left Column (80% of the space) */}
      <Grid.Column width={12}>
        {/* Content of the left column */}
        {/* You can add your components/content here */}
        <Segment style={{ height: "100%", width: "100%" }}>
          <LoadScript googleMapsApiKey={import.meta.env.VITE_GMAPS_API_KEY}>
            <style scoped>{remove_button_css}</style>
            <GoogleMap
              mapContainerStyle={{ height: "100%", width: "100%" }} //TODO change this to classname
              center={defaultCenter}
              zoom={13}
              options={{
                mapTypeControl: false,
                streetViewControl: false,
                mapId: import.meta.env.VITE_MAP_ID,
              }}
            >
              {markers.map((marker) => (
                <MarkerF
                  key={marker.id}
                  position={marker.position}
                  onMouseOver={() => handleMarkerClick(marker)}
                  onMouseOut={() => handleInfoWindowClose()}
                  icon={dotUrl}
                >
                  {selectedMarker && selectedMarker.id === marker.id && (
                    <InfoWindowF position={selectedMarker.position}>
                      <div>{selectedMarker.content}</div>
                    </InfoWindowF>
                  )}
                </MarkerF>
              ))}
            </GoogleMap>
          </LoadScript>
        </Segment>
      </Grid.Column>

      {/* Right Column (Split into 2 sections) */}
      <Grid.Column width={4}>
        {/* First section in the right column */}
        <Grid.Row style={{ height: "50%", width: "100%" }}>
          <Header>Progress</Header>
        </Grid.Row>

        {/* Second section in the right column */}
        <Grid.Row style={{ height: "50%", width: "100%" }}>
          {/* Content of the second section */}
          {/* You can add your components/content here */}
          <Header>Logs</Header>
        </Grid.Row>
      </Grid.Column>
    </Grid>
  );
}
