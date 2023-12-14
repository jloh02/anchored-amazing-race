import { useState, useEffect } from "react";
import "./App.css";
import { initializeAuth } from "firebase/auth";
import { initializeApp } from "firebase/app";
import Login from "./login.js";
import { GoogleAuthProvider, signInWithCredential } from "firebase/auth";
import {
  initializeFirestore,
  doc,
  getDoc,
  Firestore,
} from "firebase/firestore";
import { Dimmer, Loader } from "semantic-ui-react";
import Dashboard from "./dashboard.js";

const app = initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: "anchored-amazing-race.firebaseapp.com",
  projectId: "anchored-amazing-race",
  storageBucket: "anchored-amazing-race.appspot.com",
  messagingSenderId: "746182411014",
  appId: "1:746182411014:web:81595f13a6f279bd949487",
  measurementId: "G-9F7S4DG3F1",
});
const auth = initializeAuth(app);

function App() {
  const [loading, setLoading] = useState(true);
  const [googleCreds, setGoogleCreds] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [db, setDb] = useState<Firestore | null>(null);

  useEffect(() => {
    if (googleCreds.length == 0) return;
    const idToken = googleCreds;
    const credential = GoogleAuthProvider.credential(idToken);

    console.log("Signed into Google");

    // Sign in with credential from the Google user.
    signInWithCredential(auth, credential)
      .catch((error) => console.error(error))
      .then(async () => {
        try {
          const db = initializeFirestore(app, {});
          setDb(db);
          await getDoc(doc(db, "admins", "_globals"));
          setAuthorized(true);
        } catch (e) {
          setAuthorized(false);
        } finally {
          setLoading(false);
        }
      });
  }, [googleCreds]);

  return (
    <>
      {!loading || (
        <Dimmer inverted active>
          <Loader inverted>Loading...</Loader>
        </Dimmer>
      )}
      <Login callback={setGoogleCreds}></Login>

      {loading || googleCreds.length == 0 || authorized || <p>Access Denied</p>}
      {loading || googleCreds.length == 0 || !authorized || (
        <Dashboard db={db} />
      )}
    </>
  );
}

export default App;
