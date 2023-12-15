import { useState, useEffect, useMemo, useRef } from "react";
import {
  GoogleMap,
  MarkerF,
  InfoWindowF,
  useJsApiLoader,
} from "@react-google-maps/api";
import {
  collection,
  query,
  onSnapshot,
  Firestore,
  Unsubscribe,
  orderBy,
  DocumentReference,
  GeoPoint,
  Timestamp,
} from "firebase/firestore";
import { Grid, Header, HeaderSubheader, Segment } from "semantic-ui-react";
import { getIcon, timeSince } from "./utils.js";

const remove_button_css = `
.gm-style-iw {
  text-align: center;
}
.gm-style-iw > button {
  display: none !important;
}`;

const DEFAULT_CENTER = { lat: 1.3521, lng: 103.8198 };

interface User {
  username: string;
  group: DocumentReference;
  registered: boolean;
  location: GeoPoint;
  last_update: Timestamp;
}

interface Marker {
  id: number;
  position: google.maps.LatLng;
  last_update: Date;
  group_num: number;
  username: string;
}

export default function Dashboard({ db }: { db: Firestore | null }) {
  const userListenerUnsubRef = useRef<Unsubscribe | undefined>();
  const groupListenerUnsubRef = useRef<Unsubscribe | undefined>();

  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState(new Map());

  const { isLoaded } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: import.meta.env.VITE_GMAPS_API_KEY,
  });

  useEffect(() => {
    if (!db) return;

    if (groupListenerUnsubRef.current) groupListenerUnsubRef.current();
    groupListenerUnsubRef.current = onSnapshot(
      collection(db, "groups"),
      (querySnapshot) => {
        console.log(querySnapshot.size, querySnapshot.metadata);
        const tmpGroups = new Map();
        querySnapshot.forEach((doc) =>
          tmpGroups.set(parseInt(doc.id), doc.data())
        );
        console.log(tmpGroups);
        setGroups(tmpGroups);
      },
      (error) => {
        console.error("Error fetching groups: ", error);
      }
    );

    if (userListenerUnsubRef.current) userListenerUnsubRef.current();
    userListenerUnsubRef.current = onSnapshot(
      query(collection(db, "users"), orderBy("location")),
      (querySnapshot) => {
        console.log(querySnapshot.size, querySnapshot.metadata);
        const tmpUsers: User[] = [];
        querySnapshot.forEach((doc) =>
          tmpUsers.push({ username: doc.id, ...doc.data() } as User)
        );
        console.log(tmpUsers);
        setUsers(tmpUsers);
      },
      (error) => {
        console.error("Error fetching users: ", error);
      }
    );
  }, [db]);

  const markers = useMemo(() => {
    if (!isLoaded) return [];
    return users.map<Marker>((user, idx) => {
      return {
        id: idx,
        position: new google.maps.LatLng(
          user.location.latitude,
          user.location.longitude
        ),
        last_update: user.last_update.toDate(),
        group_num: parseInt(user.group.id),
        username: user.username,
      };
    });
  }, [users, isLoaded]);

  useEffect(() => {
    console.log(markers, groups, users);
  }, [markers, groups, users]);

  const handleMarkerClick = (marker: Marker) => {
    setSelectedMarker(marker);
  };

  // Handle info window close event
  const handleInfoWindowClose = () => {
    setSelectedMarker(null);
  };

  const [selectedMarker, setSelectedMarker] = useState<Marker | null>(null);

  if (!db) return <Header>Firestore DB null</Header>;

  return (
    <Grid style={{ height: "100%", width: "100%" }}>
      {/* Left Column (80% of the space) */}
      <Grid.Column width={12}>
        {/* Content of the left column */}
        {/* You can add your components/content here */}
        <Segment style={{ height: "100%", width: "100%" }}>
          {isLoaded && (
            <>
              <style scoped>{remove_button_css}</style>
              <GoogleMap
                mapContainerStyle={{ height: "100%", width: "100%" }} //TODO change this to classname
                center={DEFAULT_CENTER}
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
                    onClick={() =>
                      window.open(`https://t.me/${marker.username}`, "_blank")
                    }
                    icon={getIcon(marker.group_num)}
                  >
                    {selectedMarker && selectedMarker.id === marker.id && (
                      <InfoWindowF position={selectedMarker.position}>
                        <>
                          <Header>
                            {
                              (groups.get(selectedMarker.group_num) ?? {
                                name: "unknown",
                              })["name"]
                            }
                          </Header>
                          <HeaderSubheader>
                            {"Username: " + selectedMarker.username}
                          </HeaderSubheader>
                          <HeaderSubheader>
                            {"Updated " +
                              timeSince(selectedMarker.last_update) +
                              " ago"}
                          </HeaderSubheader>
                        </>
                      </InfoWindowF>
                    )}
                  </MarkerF>
                ))}
              </GoogleMap>
            </>
          )}
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