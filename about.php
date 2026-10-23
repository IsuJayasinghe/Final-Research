<?php
$pageTitle = 'About Smart Port AI | Terminal Overview';
$activeNav = 'about';

$stats = [
    ['label' => 'Annual Throughput', 'value' => '4.8M TEU', 'note' => 'Designed terminal volume', 'class' => 'green'],
    ['label' => 'Deepwater Berths', 'value' => '6 Berths', 'note' => '2,400m continuous quay line', 'class' => ''],
    ['label' => 'Yard Storage Blocks', 'value' => '32 Blocks', 'note' => 'Zones A, B, C and D', 'class' => 'green'],
    ['label' => 'Haulage Fleet', 'value' => '30 Units', 'note' => 'Connected trucks & AGVs', 'class' => 'green'],
];

$specs = [
    [
        'asset' => 'Deepwater Quay Line',
        'dimension' => '2,400 meters / 16.5m depth',
        'equipment' => '18 Super Post-Panamax STS Cranes',
        'tech' => 'Tandem lift & laser docking aid',
        'status' => 'Operational',
        'statusClass' => 'active'
    ],
    [
        'asset' => 'Container Stacking Yard',
        'dimension' => '120,000 TEU static storage',
        'equipment' => '36 Automated Rail Gantries (ARMG)',
        'tech' => '3D AI Reshuffle Minimization',
        'status' => 'Operational',
        'statusClass' => 'active'
    ],
    [
        'asset' => 'Internal Haulage Roadways',
        'dimension' => '14 Bi-directional transit lanes',
        'equipment' => '30 Heavy Haulers & Electric AGVs',
        'tech' => 'DGPS RTK + LiDAR collision avoidance',
        'status' => 'Operational',
        'statusClass' => 'active'
    ],
    [
        'asset' => 'Smart Gate Complex',
        'dimension' => '16 Automated entrance/exit lanes',
        'equipment' => 'High-resolution OCR gantries',
        'tech' => 'Weigh-in-motion + biometric clearance',
        'status' => 'Operational',
        'statusClass' => 'active'
    ],
    [
        'asset' => 'Command & Server Center',
        'dimension' => 'Dual redundant data nodes',
        'equipment' => 'Ultra-low latency edge servers',
        'tech' => 'Private Port 5G mesh network',
        'status' => 'Certified',
        'statusClass' => 'completed'
    ],
];

$highlights = [
    ['title' => 'AI Dispatch Engine', 'class' => 'green', 'text' => 'Hybrid heuristic and reinforcement learning algorithms compute conflict-free vehicle trajectories in milliseconds.'],
    ['title' => 'Port 5G Telemetry', 'class' => '', 'text' => 'Dedicated private terminal radio infrastructure guarantees sub-15ms latency across all quay and yard zones.'],
    ['title' => 'ISPS Code Compliant', 'class' => 'green', 'text' => 'Certified in compliance with International Ship and Port Facility Security requirements.'],
    ['title' => 'Software Version', 'class' => 'orange', 'text' => 'Smart Port AI Management Suite v2.6.4 (Enterprise Maritime Edition).'],
];

include 'header.php';
?>

<main>
    <div class="page-container">

        <h1 class="page-title">About Smart Port AI System</h1>
        <p class="page-description">
            Next-generation container terminal automation architecture, infrastructure capacity,
            and real-time logistics optimization standards.
        </p>

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

        <section class="dashboard-grid">

            <div class="panel">
                <h2 class="panel-title">Terminal Infrastructure & Specifications</h2>

                <table>
                    <thead>
                    <tr>
                        <th>Asset / Facility</th>
                        <th>Capacity / Dimension</th>
                        <th>Terminal Equipment</th>
                        <th>Core Technology</th>
                        <th>Status</th>
                    </tr>
                    </thead>

                    <tbody>
                    <?php foreach ($specs as $spec): ?>
                        <tr>
                            <td><strong><?php echo htmlspecialchars($spec['asset']); ?></strong></td>
                            <td><?php echo htmlspecialchars($spec['dimension']); ?></td>
                            <td><?php echo htmlspecialchars($spec['equipment']); ?></td>
                            <td><?php echo htmlspecialchars($spec['tech']); ?></td>
                            <td>
                                <span class="status <?php echo htmlspecialchars($spec['statusClass']); ?>">
                                    <?php echo htmlspecialchars($spec['status']); ?>
                                </span>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>

            <div class="panel">
                <h2 class="panel-title">Architecture Highlights</h2>

                <?php foreach ($highlights as $hl): ?>
                    <div class="alert-item">
                        <div class="alert-title <?php echo htmlspecialchars($hl['class']); ?>">
                            <?php echo htmlspecialchars($hl['title']); ?>
                        </div>
                        <div class="alert-text">
                            <?php echo htmlspecialchars($hl['text']); ?>
                        </div>
                    </div>
                <?php endforeach; ?>
            </div>

        </section>

    </div>
</main>

<?php include 'footer.php'; ?>
