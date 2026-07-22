import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./components/Login";
import GoogleCallback from "./components/GoogleCallback";
import Dashboard from "./components/Dashboard";
import Devices from "./components/Devices";
import Cases from "./components/Cases";
import Evidence from "./components/Evidence";
import RecoveredFiles from "./components/RecoveredFiles";
import Analysis from "./components/Analysis";
import Reports from "./components/Reports";
import Settings from "./components/Settings";
import Users from "./components/Users";
import AIAssistant from "./components/AIAssistant";
import AppToaster from "./components/AppToaster";
import RoleGuard from "./components/RoleGuard";
import FileMonitor from "./components/FileMonitor";
import AuditLogs from "./components/AuditLogs";
import PermissionsAudit from "./components/PermissionsAudit";
import RecoveryJobs from "./components/RecoveryJobs";
import Timeline from "./components/Timeline";
import HashVerification from "./components/HashVerification";
import ChainOfCustody from "./components/ChainOfCustody";
import Downloads from "./components/Downloads";
import EvidencePreview from "./components/EvidencePreview";

export default function App() {
  return (
    <>
      <AppToaster />
      <Routes>
        {/* Public route */}
        <Route path="/" element={<Login />} />
        <Route path="/oauth/callback/google" element={<GoogleCallback />} />

        {/* Protected routes - all authenticated users */}
        <Route path="/dashboard" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Dashboard />} />
        </Route>

        <Route path="/ai-assistant" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<AIAssistant />} />
        </Route>

        <Route path="/cases" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Cases />} />
        </Route>

        <Route path="/evidence" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Evidence />} />
        </Route>

        <Route path="/recovered-files" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<RecoveredFiles />} />
        </Route>

        <Route path="/recovery-jobs" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<RecoveryJobs />} />
        </Route>

        <Route path="/timeline" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Timeline />} />
        </Route>

        <Route path="/hash-verification" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<HashVerification />} />
        </Route>

        <Route path="/chain-of-custody" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<ChainOfCustody />} />
        </Route>

        <Route path="/downloads" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Downloads />} />
        </Route>

        <Route path="/evidence-preview" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<EvidencePreview />} />
        </Route>

        <Route path="/analysis" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Analysis />} />
        </Route>

        <Route path="/reports" element={
          <RoleGuard allowedRoles={['analyst', 'investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Reports />} />
        </Route>

        {/* Admin + Investigator only */}
        <Route path="/devices" element={
          <RoleGuard allowedRoles={['investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Devices />} />
        </Route>

        <Route path="/file-monitor" element={
          <RoleGuard allowedRoles={['investigator', 'admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<FileMonitor />} />
        </Route>

        {/* Admin only */}
        <Route path="/settings" element={
          <RoleGuard allowedRoles={['admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Settings />} />
        </Route>

        <Route path="/users" element={
          <RoleGuard allowedRoles={['admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<Users />} />
        </Route>

        <Route path="/permissions-audit" element={
          <RoleGuard allowedRoles={['admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<PermissionsAudit />} />
        </Route>

        <Route path="/audit-logs" element={
          <RoleGuard allowedRoles={['admin']}>
            <Layout />
          </RoleGuard>
        }>
          <Route index element={<AuditLogs />} />
        </Route>
      </Routes>
    </>
  );
}
