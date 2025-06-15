import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  IconButton,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Divider,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  CardHeader,
  Collapse,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Search as SearchIcon,
  Clear as ClearIcon,
  DeleteOutline as DeleteOutlineIcon,
} from "@mui/icons-material";

import api from "../../services/api";
import { useAuthStore } from "../../contexts/authStore";

// Define log level colors
const LOG_LEVEL_COLORS = {
  DEBUG: "#6c757d", // grey
  INFO: "#0d6efd", // blue
  WARNING: "#ffc107", // yellow
  ERROR: "#dc3545", // red
  CRITICAL: "#7209b7", // purple
};

const LogViewer = () => {
  const [logFiles, setLogFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [logEntries, setLogEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [filterLevel, setFilterLevel] = useState("");
  const [expandedEntries, setExpandedEntries] = useState({});
  const [error, setError] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);
  const [isLoadingSystemInfo, setIsLoadingSystemInfo] = useState(false);

  useEffect(() => {
    // Load log files
    fetchLogFiles();
  }, []);

  const fetchLogFiles = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get("/api/logs/files");
      setLogFiles(response.data);
      
      // Select first file by default if not already selected
      if (response.data.length > 0 && !selectedFile) {
        setSelectedFile(response.data[0].name);
        fetchLogEntries(response.data[0].name);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load log files");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchLogEntries = async (fileName = selectedFile) => {
    if (!fileName) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(
        `/api/logs/${fileName}?max_lines=1000${filterLevel ? `&filter_level=${filterLevel}` : ""}${filterText ? `&filter_text=${encodeURIComponent(filterText)}` : ""}`
      );
      setLogEntries(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load log entries");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSystemInfo = async () => {
    setIsLoadingSystemInfo(true);
    setError(null);

    try {
      const response = await api.get("/api/logs/system-info");
      setSystemInfo(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load system information");
    } finally {
      setIsLoadingSystemInfo(false);
    }
  };

  const downloadLogFile = (fileName) => {
    window.open(`${api.defaults.baseURL}/api/logs/${fileName}/download`, "_blank");
  };

  const handleFileChange = (fileName) => {
    setSelectedFile(fileName);
    fetchLogEntries(fileName);
  };

  const handleFilterApply = () => {
    fetchLogEntries();
  };

  const handleFilterClear = () => {
    setFilterText("");
    setFilterLevel("");
    fetchLogEntries(selectedFile);
  };

  const toggleExpand = (index) => {
    setExpandedEntries((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const formatLogEntry = (entry, index) => {
    const isExpanded = expandedEntries[index] || false;
    const isJsonObject = typeof entry === "object" && entry !== null;

    if (!isJsonObject) {
      return (
        <TableRow key={index}>
          <TableCell colSpan={4}>{String(entry)}</TableCell>
        </TableRow>
      );
    }

    const timestamp = entry.timestamp || "";
    const level = entry.level || "INFO";
    const message = entry.message || "";
    const logger = entry.logger || "";

    return (
      <React.Fragment key={index}>
        <TableRow
          sx={{
            cursor: "pointer",
            "&:hover": { backgroundColor: "rgba(0, 0, 0, 0.04)" },
            backgroundColor: isExpanded ? "rgba(0, 0, 0, 0.04)" : "inherit",
          }}
          onClick={() => toggleExpand(index)}
        >
          <TableCell sx={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {timestamp}
          </TableCell>
          <TableCell>
            <Chip
              label={level}
              size="small"
              sx={{
                backgroundColor: LOG_LEVEL_COLORS[level] || "#6c757d",
                color: level === "WARNING" ? "#000" : "#fff",
              }}
            />
          </TableCell>
          <TableCell sx={{ maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {logger}
          </TableCell>
          <TableCell sx={{ maxWidth: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {message}
          </TableCell>
          <TableCell align="right">
            {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </TableCell>
        </TableRow>
        {isExpanded && (
          <TableRow>
            <TableCell colSpan={5} sx={{ padding: 0 }}>
              <Paper sx={{ margin: 1, padding: 2, backgroundColor: "#f8f9fa" }}>
                <pre
                  style={{
                    overflow: "auto",
                    maxHeight: "300px",
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-all",
                  }}
                >
                  {JSON.stringify(entry, null, 2)}
                </pre>
              </Paper>
            </TableCell>
          </TableRow>
        )}
      </React.Fragment>
    );
  };

  return (
    <Box sx={{ padding: 2 }}>
      <Typography variant="h4" gutterBottom>
        Log Viewer
      </Typography>

      {error && (
        <Alert severity="error" sx={{ marginBottom: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ padding: 2, marginBottom: 2 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
              <Typography variant="h6">Log Files</Typography>
              <IconButton size="small" onClick={fetchLogFiles} title="Refresh log files">
                <RefreshIcon />
              </IconButton>
            </Box>
            <Divider sx={{ marginBottom: 2 }} />
            {isLoading && !logFiles.length ? (
              <Box sx={{ display: "flex", justifyContent: "center", padding: 2 }}>
                <CircularProgress size={24} />
              </Box>
            ) : (
              <Box component="ul" sx={{ padding: 0, margin: 0, listStyle: "none" }}>
                {logFiles.map((file) => (
                  <Box
                    component="li"
                    key={file.name}
                    sx={{
                      marginBottom: 1,
                      padding: 1,
                      borderRadius: 1,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      cursor: "pointer",
                      backgroundColor: selectedFile === file.name ? "#e3f2fd" : "transparent",
                      "&:hover": { backgroundColor: selectedFile === file.name ? "#e3f2fd" : "#f5f5f5" },
                    }}
                    onClick={() => handleFileChange(file.name)}
                  >
                    <Typography variant="body2" noWrap title={file.name}>
                      {file.name}
                    </Typography>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        downloadLogFile(file.name);
                      }}
                      title="Download log file"
                    >
                      <DownloadIcon fontSize="small" />
                    </IconButton>
                  </Box>
                ))}
              </Box>
            )}
          </Paper>

          <Paper sx={{ padding: 2 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
              <Typography variant="h6">System Info</Typography>
              <Button
                variant="outlined"
                size="small"
                onClick={fetchSystemInfo}
                startIcon={isLoadingSystemInfo ? <CircularProgress size={16} /> : <RefreshIcon />}
                disabled={isLoadingSystemInfo}
              >
                {systemInfo ? "Refresh" : "Load"}
              </Button>
            </Box>
            <Divider sx={{ marginBottom: 2 }} />

            {systemInfo ? (
              <Box sx={{ overflowY: "auto", maxHeight: "300px" }}>
                <Typography variant="subtitle2" gutterBottom>
                  Platform: {systemInfo.platform.system} {systemInfo.platform.release}
                </Typography>
                <Typography variant="subtitle2" gutterBottom>
                  Python: {systemInfo.python.version.split(" ")[0]}
                </Typography>
                <Typography variant="subtitle2" gutterBottom>
                  Memory: {systemInfo.memory.used}GB / {systemInfo.memory.total}GB ({systemInfo.memory.percent}%)
                </Typography>
                <Typography variant="subtitle2" gutterBottom>
                  Disk: {systemInfo.disk.used}GB / {systemInfo.disk.total}GB ({systemInfo.disk.percent}%)
                </Typography>
                <Typography variant="subtitle2" gutterBottom>
                  CPU: {systemInfo.cpu.percent}% (Cores: {systemInfo.cpu.count})
                </Typography>
                <Typography variant="subtitle2" gutterBottom>
                  Time: {new Date(systemInfo.time.now).toLocaleString()}
                </Typography>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary" align="center">
                Click load to view system information
              </Typography>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={9}>
          <Paper sx={{ padding: 2 }}>
            <Box sx={{ marginBottom: 2 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} md={3}>
                  <FormControl fullWidth variant="outlined" size="small">
                    <InputLabel id="filter-level-label">Log Level</InputLabel>
                    <Select
                      labelId="filter-level-label"
                      value={filterLevel}
                      onChange={(e) => setFilterLevel(e.target.value)}
                      label="Log Level"
                    >
                      <MenuItem value="">All Levels</MenuItem>
                      <MenuItem value="DEBUG">DEBUG</MenuItem>
                      <MenuItem value="INFO">INFO</MenuItem>
                      <MenuItem value="WARNING">WARNING</MenuItem>
                      <MenuItem value="ERROR">ERROR</MenuItem>
                      <MenuItem value="CRITICAL">CRITICAL</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    size="small"
                    variant="outlined"
                    placeholder="Filter by text..."
                    value={filterText}
                    onChange={(e) => setFilterText(e.target.value)}
                    InputProps={{
                      startAdornment: <SearchIcon fontSize="small" sx={{ marginRight: 1, color: "text.secondary" }} />,
                      endAdornment: filterText ? (
                        <IconButton size="small" onClick={() => setFilterText("")}>
                          <ClearIcon fontSize="small" />
                        </IconButton>
                      ) : null,
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={3}>
                  <Box sx={{ display: "flex", gap: 1 }}>
                    <Button
                      variant="contained"
                      color="primary"
                      fullWidth
                      onClick={handleFilterApply}
                      disabled={isLoading}
                    >
                      Filter
                    </Button>
                    <Button
                      variant="outlined"
                      fullWidth
                      onClick={handleFilterClear}
                      disabled={isLoading || (!filterText && !filterLevel)}
                    >
                      Clear
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </Box>

            <Box sx={{ position: "relative", minHeight: "400px" }}>
              {isLoading && (
                <Box
                  sx={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: "rgba(255, 255, 255, 0.7)",
                    zIndex: 1,
                  }}
                >
                  <CircularProgress />
                </Box>
              )}

              <TableContainer sx={{ maxHeight: "calc(100vh - 300px)" }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>Level</TableCell>
                      <TableCell>Logger</TableCell>
                      <TableCell>Message</TableCell>
                      <TableCell align="right">Details</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {logEntries.length > 0 ? (
                      logEntries.map((entry, index) => formatLogEntry(entry, index))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          {selectedFile ? "No log entries found" : "Select a log file to view entries"}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default LogViewer;
