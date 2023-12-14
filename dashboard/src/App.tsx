import { useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";
import { initializeAuth } from "firebase/auth";
import { initializeApp } from "firebase/app";
import Login from "./login";

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
  const [count, setCount] = useState(0);

  return (
    <>
      <div>
        <a href="https://vitejs.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
      <Login auth={auth}></Login>
    </>
  );
}

export default App;
