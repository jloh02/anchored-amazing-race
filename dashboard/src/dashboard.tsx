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
import {
  Button,
  Card,
  Container,
  Feed,
  Grid,
  Header,
  HeaderSubheader,
  Loader,
  Modal,
  Segment,
} from "semantic-ui-react";
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import {
  getIcon,
  getProgress,
  getProgressStr,
  Group,
  timeSince,
} from "./utils.js";

const custom_css = `
.gm-style-iw {
  text-align: center;
}
.gm-style-iw > button {
  display: none !important;
}
.ui.dimmer .ui.modal .ui.loader:before {
  border-color: rgba(0,0,0,.1);
}
.ui.dimmer .ui.modal .ui.loader:after {
  border-color: #767676 transparent transparent;
}          
.ui.dimmer .ui.modal .ui.loader p {
  color: #767676;
}
`;

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
  group_name: string;
  username: string;
  icon: string;
}

export default function Dashboard({ db }: { db: Firestore | null }) {
  const userListenerUnsubRef = useRef<Unsubscribe | undefined>();
  const groupListenerUnsubRef = useRef<Unsubscribe | undefined>();
  const approvalListenerUnsubRef = useRef<Unsubscribe | undefined>();

  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState<Map<string, Group>>(new Map());
  const [logs, setLogs] = useState("");

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
        const tmpGroups = new Map();
        let idx = 0;
        querySnapshot.forEach((doc) => {
          tmpGroups.set(doc.id, { key: idx, ...doc.data() } as Group);
          idx++;
        });
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
        const tmpUsers: User[] = [];
        querySnapshot.forEach((doc) =>
          tmpUsers.push({ username: doc.id, ...doc.data() } as User)
        );
        setUsers(tmpUsers);
      },
      (error) => {
        console.error("Error fetching users: ", error);
      }
    );

    if (approvalListenerUnsubRef.current) approvalListenerUnsubRef.current();
    approvalListenerUnsubRef.current = onSnapshot(
      collection(db, "approvals"),
      (querySnapshot) => {
        querySnapshot
          .docChanges()
          .filter((value) => value.type === "added")
          .filter((value) => value.doc.id !== "placeholder")
          .forEach((value) => toast(`New approval request: ${value.doc.id}`));
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
        group_name: user.group.id,
        last_update: user.last_update.toDate(),
        username: user.username,
        icon: getIcon(groups.get(user.group.id)?.key ?? 0, true),
      };
    });
  }, [users, groups, isLoaded]);

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
      <Grid.Column width={12}>
        <ToastContainer
          autoClose={30000}
          pauseOnHover={false}
          position="top-left"
        />
        <Segment style={{ height: "100%", width: "100%", margin: 0 }}>
          {isLoaded && (
            <>
              <style scoped>{custom_css}</style>
              <GoogleMap
                mapContainerStyle={{ height: "100%", width: "100%" }}
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
                    icon={marker.icon}
                  >
                    {selectedMarker && selectedMarker.id === marker.id && (
                      <InfoWindowF position={selectedMarker.position}>
                        <>
                          <Header>
                            {
                              (groups.get(selectedMarker.group_name) ?? {
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
      <Grid.Column
        width={4}
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          width: "100%",
        }}
      >
        <>
          <Card style={{ height: "100%", width: "100%" }}>
            <Card.Content
              style={{ height: "100%", width: "100%", paddingBottom: "3rem" }}
            >
              <Header>Leaderboard</Header>
              <div
                style={{
                  height: "100%",
                  overflowY: "scroll",
                }}
              >
                {Array.from(groups.values())
                  .sort((a, b) => {
                    const progA = getProgress(a);
                    const progB = getProgress(b);
                    if (progA === progB) return a.name.localeCompare(b.name);
                    return progB - progA;
                  })
                  .map((group, idx) => (
                    <Feed key={idx}>
                      <Feed.Event style={{ height: "" }}>
                        <Feed.Label
                          image={getIcon(group.key ?? 0)}
                          style={{ margin: "auto 0 auto 0" }}
                        />
                        <Feed.Content>
                          <Feed.Summary>{group.name}</Feed.Summary>
                          <p>{getProgressStr(group)}</p>
                        </Feed.Content>
                      </Feed.Event>
                    </Feed>
                  ))}
              </div>
            </Card.Content>
          </Card>
          <div style={{ display: "flex", width: "100%" }}>
            <Modal
              size="large"
              trigger={
                <Button primary style={{ flex: 1 }}>
                  <p>Show Logs</p>
                </Button>
              }
              onOpen={async () => {
                const res = await fetch(
                  `${import.meta.env.VITE_BACKEND_API}logs/err`
                );
                setLogs(await res.text());
              }}
              onClose={() => setLogs("")}
              active
            >
              <Modal.Header>Logs</Modal.Header>
              <Container style={{ maxHeight: "70vh", padding: "2em" }}>
                <Modal.Content
                  scrolling
                  style={
                    logs.length
                      ? {
                          padding: 0,
                        }
                      : {
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          minHeight: 100,
                        }
                  }
                >
                  {logs.length ? (
                    <pre
                      style={{
                        margin: 0,
                        whiteSpace: "pre-wrap",
                        backgroundColor: "black",
                        color: "white",
                      }}
                    >
                      {logs}
                    </pre>
                  ) : (
                    <Loader active inline>
                      <p>Loading...</p>
                    </Loader>
                  )}
                </Modal.Content>
              </Container>
            </Modal>
            <Button
              primary
              style={{ flex: 1 }}
              href="https://t.me/anchored_amazing_race_bot"
              target="_blank"
            >
              <p>Open Bot</p>
            </Button>
          </div>
        </>
      </Grid.Column>
    </Grid>
  );
}
