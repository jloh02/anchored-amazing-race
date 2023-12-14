import { useState, useEffect } from "react";
import { Modal } from "semantic-ui-react";
import { Auth, EmailAuthProvider } from "firebase/auth";
import * as firebaseui from "firebaseui";

function Login({ auth }: { auth: Auth }) {
  const [open, setOpen] = useState(true);
  // const [email, setEmail] = useState("");
  // const [password, setPassword] = useState("");

  useEffect(() => {
    const ui =
      firebaseui.auth.AuthUI.getInstance() || new firebaseui.auth.AuthUI(auth);
    ui.start("#firebase-auth-container", {
      signInOptions: [
        {
          provider: EmailAuthProvider.PROVIDER_ID,
          requireDisplayName: false,
          // disableSignUp: { status: true },
        },
      ],
      callbacks: {
        signInSuccessWithAuthResult: (authResult, redirectUrl) => {
          setOpen(false);
          return false;
        },
      },
    });
  }, [auth]);

  return (
    <>
      <Modal
        closeOnEscape={false}
        closeOnDimmerClick={false}
        open={open}
        onClose={() => {
          "WEEEEEEEE";
        }}
      >
        <Modal.Content>
          <div id="firebase-auth-container"></div>
        </Modal.Content>
      </Modal>
    </>
  );
}

export default Login;
