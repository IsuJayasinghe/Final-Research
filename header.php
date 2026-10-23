<?php
// Default values if not defined by calling page
if (!isset($pageTitle)) {
    $pageTitle = 'Smart Port | AI Management System';
}
if (!isset($activeNav)) {
    $activeNav = 'home';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars($pageTitle); ?></title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>

<header class="header">
    <a href="dashboard.php" class="logo">
        <div class="logo-icon">⚓</div>
        <div>
            <div class="logo-title">SMART PORT</div>
            <div class="logo-subtitle">AI MANAGEMENT SYSTEM</div>
        </div>
    </a>

    <nav class="nav">
        <a href="dashboard.php" class="<?php echo ($activeNav === 'home') ? 'active' : ''; ?>">Home</a>
        <a href="task-assignment.php" class="<?php echo ($activeNav === 'solutions') ? 'active' : ''; ?>">Solutions⌄</a>
        <a href="live-tracking.php" class="<?php echo ($activeNav === 'tracking') ? 'active' : ''; ?>">Live Tracking</a>
        <a href="task-management.php" class="<?php echo ($activeNav === 'tasks') ? 'active' : ''; ?>">Tasks</a>
        <a href="analytics.php" class="<?php echo ($activeNav === 'analytics') ? 'active' : ''; ?>">Analytics</a>
    </nav>

    <input class="search-box" type="text" placeholder="⌕  Search">

    <div class="header-actions">
        <div class="notification" title="Alerts">
            ♧
            <span class="badge">3</span>
        </div>
        <div class="profile" title="Operator Profile">♙</div>
    </div>
</header>
