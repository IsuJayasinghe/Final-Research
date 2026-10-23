<?php
$pageTitle = 'Performance Analytics | Smart Port';
$activeNav = 'analytics';

$stats = [
    ['label' => 'Average Waiting Time', 'value' => '6.8 min', 'note' => 'Current operational average', 'class' => 'green'],
    ['label' => 'Average Task Completion', 'value' => '14.2 min', 'note' => 'Across completed tasks', 'class' => ''],
    ['label' => 'Truck Utilization', 'value' => '82%', 'note' => 'Current fleet utilization', 'class' => 'green'],
    ['label' => 'Completed Transfers', 'value' => '38', 'note' => 'Current operational period', 'class' => ''],
];

$fleetMetrics = [
    ['label' => 'Active Transportation', 'val' => '58%'],
    ['label' => 'Loading / Unloading', 'val' => '24%'],
    ['label' => 'Available / Idle', 'val' => '12%'],
    ['label' => 'Delayed', 'val' => '6%'],
];

$barChart = [
    ['time' => '08:00', 'height' => '80px'],
    ['time' => '10:00', 'height' => '120px'],
    ['time' => '12:00', 'height' => '155px'],
    ['time' => '14:00', 'height' => '110px'],
    ['time' => '16:00', 'height' => '175px'],
    ['time' => '18:00', 'height' => '140px'],
];

$kpiRows = [
    ['indicator' => 'Average Truck Waiting Time', 'value' => '6.8 min', 'status' => 'Normal', 'class' => 'green'],
    ['indicator' => 'Average Empty Travel Distance', 'value' => '1.7 km', 'status' => 'Normal', 'class' => 'green'],
    ['indicator' => 'Average Task Completion Time', 'value' => '14.2 min', 'status' => 'Normal', 'class' => 'green'],
    ['indicator' => 'Truck Utilization', 'value' => '82%', 'status' => 'Good', 'class' => 'green'],
    ['indicator' => 'Average Congestion Delay', 'value' => '3.1 min', 'status' => 'Monitor', 'class' => 'orange'],
    ['indicator' => 'Completed Container Transfers', 'value' => '38', 'status' => 'On Track', 'class' => 'green'],
];

include 'header.php';
?>

<main>
<div class="page-container">

    <h1 class="page-title">Performance & Analytics</h1>

    <p class="page-description">
        Review truck utilization, transportation efficiency and
        operational performance indicators.
    </p>

    <div class="analytics-filter">
        <select>
            <option>Today</option>
            <option>Last 7 Days</option>
            <option>Last 30 Days</option>
            <option>Custom Period</option>
        </select>
    </div>

    <section class="stats-grid">
        <?php foreach ($stats as $stat): ?>
            <div class="stat-card">
                <div class="stat-label"><?php echo htmlspecialchars($stat['label']); ?></div>
                <div class="stat-value"><?php echo htmlspecialchars($stat['value']); ?></div>
                <div class="stat-note <?php echo htmlspecialchars($stat['class']); ?>">
                    <?php echo htmlspecialchars($stat['note']); ?>
                </div>
            </div>
        <?php endforeach; ?>
    </section>

    <div class="analytics-grid">

        <div class="panel">
            <h2 class="panel-title">Fleet Utilization</h2>

            <?php foreach ($fleetMetrics as $m): ?>
                <div class="metric-row">
                    <div class="metric-header">
                        <span><?php echo htmlspecialchars($m['label']); ?></span>
                        <strong><?php echo htmlspecialchars($m['val']); ?></strong>
                    </div>
                    <div class="progress">
                        <div class="progress-fill" style="width:<?php echo htmlspecialchars($m['val']); ?>;"></div>
                    </div>
                </div>
            <?php endforeach; ?>
        </div>

        <div class="panel">
            <h2 class="panel-title">Completed Transfers by Time Period</h2>

            <div class="bar-chart">
                <?php foreach ($barChart as $b): ?>
                    <div class="bar-group">
                        <div class="bar" style="height:<?php echo htmlspecialchars($b['height']); ?>;"></div>
                        <div class="bar-label"><?php echo htmlspecialchars($b['time']); ?></div>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>

    </div>

    <div class="panel" style="margin-top:22px;">
        <h2 class="panel-title">Operational Performance Summary</h2>

        <table class="comparison-table">
            <thead>
            <tr>
                <th>Performance Indicator</th>
                <th>Current Value</th>
                <th>Operational Status</th>
            </tr>
            </thead>

            <tbody>
            <?php foreach ($kpiRows as $row): ?>
                <tr>
                    <td><?php echo htmlspecialchars($row['indicator']); ?></td>
                    <td><?php echo htmlspecialchars($row['value']); ?></td>
                    <td class="<?php echo htmlspecialchars($row['class']); ?>">
                        <?php echo htmlspecialchars($row['status']); ?>
                    </td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </div>

</div>
</main>

<?php include 'footer.php'; ?>
