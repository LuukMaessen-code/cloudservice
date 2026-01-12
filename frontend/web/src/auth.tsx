import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import keycloak from "./keycloak";

const AuthContext = createContext({
  keycloak: keycloak,
  initialized: false,
  authenticated: false,
  token: undefined as string | undefined,
  username: undefined as string | undefined,
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [initialized, setInitialized] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [token, setToken] = useState<string | undefined>(undefined);
  const [username, setUsername] = useState<string | undefined>(undefined);
  const initRef = useRef(false);

  useEffect(() => {
    if (!initRef.current) {
      initRef.current = true;
      keycloak.init({ onLoad: "login-required" }).then((auth) => {
        setInitialized(true);
        setAuthenticated(auth);
        if (auth) {
          setToken(keycloak.token);
          setUsername(keycloak.tokenParsed?.preferred_username || keycloak.tokenParsed?.sub);
        }
      });
      keycloak.onAuthSuccess = () => {
        setAuthenticated(true);
        setToken(keycloak.token);
        setUsername(keycloak.tokenParsed?.preferred_username || keycloak.tokenParsed?.sub);
      };
      keycloak.onAuthLogout = () => {
        setAuthenticated(false);
        setToken(undefined);
        setUsername(undefined);
      };
    }
  }, []);

  return (
    <AuthContext.Provider value={{ keycloak, initialized, authenticated, token, username }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
