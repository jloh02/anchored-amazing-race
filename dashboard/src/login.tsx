import { useState } from "react";
import { Modal } from "semantic-ui-react";
import { GoogleLogin } from "@react-oauth/google";

function Login({ callback }: { callback: (creds: string) => void }) {
  const [open, setOpen] = useState(true);

  return (
    <>
      <Modal
        closeOnEscape={false}
        closeOnDimmerClick={false}
        open={open}
        style={{ width: "fit-content" }}
      >
        <Modal.Header>Sign In</Modal.Header>
        <Modal.Content>
          <p>Authorized Users Only!</p>
          <GoogleLogin
            onSuccess={(res) => {
              callback(res.credential ?? "");
              setOpen(false);
            }}
            onError={() => {
              console.log("ERROR");
            }}
          />
        </Modal.Content>
      </Modal>
    </>
  );
}

export default Login;
