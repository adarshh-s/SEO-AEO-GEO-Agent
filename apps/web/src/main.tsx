import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import { SessionBootstrap } from "./app/bootstrap";
import { Providers } from "./app/providers";
import { router } from "./app/router";
import { PRODUCT_NAME } from "./lib/brand";
import "./lib/i18n";
import "./index.css";

document.title = PRODUCT_NAME;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Providers>
      <SessionBootstrap>
        <RouterProvider router={router} />
      </SessionBootstrap>
    </Providers>
  </StrictMode>,
);
