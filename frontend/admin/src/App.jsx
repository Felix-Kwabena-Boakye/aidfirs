import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";
import Devices from "./components/Devices";
import Cases from "./components/Cases";
import Evidence from "./components/Evidence";
import Analysis from "./components/Analysis";
import Reports from "./components/Reports";
import Settings from "./components/Settings";
import Users from "./components/Users";
import AIAssistant from "./components/AIAssistant";
import AppToaster from "./components/AppToaster";

export default function App() {
  return (
    <>
      <AppToaster />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Layout />}>
          <Route index element={<Dashboard />} />
        </Route>
        <Route path="/ai-assistant" element={<Layout />}>
          <Route index element={<AIAssistant />} />
        </Route>
        <Route path="/devices" element={<Layout />}>
          <Route index element={<Devices />} />
        </Route>
        <Route path="/cases" element={<Layout />}>
          <Route index element={<Cases />} />
        </Route>
        <Route path="/evidence" element={<Layout />}>
          <Route index element={<Evidence />} />
        </Route>
        <Route path="/analysis" element={<Layout />}>
          <Route index element={<Analysis />} />
        </Route>
        <Route path="/reports" element={<Layout />}>
          <Route index element={<Reports />} />
        </Route>
        <Route path="/settings" element={<Layout />}>
          <Route index element={<Settings />} />
        </Route>
        <Route path="/users" element={<Layout />}>
          <Route index element={<Users />} />
        </Route>
      </Routes>
    </>
  );
}
