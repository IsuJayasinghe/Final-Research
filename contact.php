<?php
$pageTitle = 'Operations Support & Contact | Smart Port';
$activeNav = 'contact';

$stats = [
    ['label' => 'Emergency Channel', 'value' => 'VHF Ch 16', 'note' => '24/7 Port safety frequency', 'class' => 'red'],
    ['label' => 'Control Desk Hotline', 'value' => '+1 (800) 555-PORT', 'note' => 'Direct terminal dispatch line', 'class' => 'green'],
    ['label' => 'Avg Response Time', 'value' => '2.4 min', 'note' => 'Rapid incident resolution', 'class' => 'green'],
    ['label' => 'Dispatchers on Duty', 'value' => '8 Active', 'note' => 'Terminal command center', 'class' => ''],
];

$contacts = [
    ['role' => 'Harbor Master & Berth Control', 'station' => 'Marine Tower (VHF 12)', 'ext' => 'Ext. 101', 'class' => 'green'],
    ['role' => 'Yard Superintendent', 'station' => 'Blocks A–D Logistics', 'ext' => 'Ext. 204', 'class' => ''],
    ['role' => 'Port Safety & Hazmat Response', 'station' => 'Fire Station 02', 'ext' => 'Ext. 911 / VHF 16', 'class' => 'red'],
    ['role' => 'AI System & IT Infrastructure', 'station' => 'Server Room B', 'ext' => 'Ext. 509', 'class' => 'orange'],
];

include 'header.php';
?>

<main>
    <div class="page-container">

        <h1 class="page-title">Terminal Control & Operations Support</h1>
        <p class="page-description">
            Connect directly with port terminal dispatchers, the harbor master office,
            safety emergency units, and AI systems engineering.
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
                <h2 class="panel-title">Submit Operations Ticket / Incident Report</h2>

                <form onsubmit="event.preventDefault(); submitInquiry();">
                    <div class="form-grid">

                        <div class="form-group">
                            <label for="operatorName">Officer / Operator Name</label>
                            <input id="operatorName" type="text" value="J. Martinez (Dispatcher #402)" required>
                        </div>

                        <div class="form-group">
                            <label for="station">Station / Call Sign</label>
                            <input id="station" type="text" value="Tower Control - Station 04" required>
                        </div>

                        <div class="form-group">
                            <label for="department">Department</label>
                            <select id="department">
                                <option>Internal Haulage & Fleet</option>
                                <option selected>Berth & Quay Crane Operations</option>
                                <option>Yard Container Stacking</option>
                                <option>Gate Security & Inspection</option>
                                <option>AI Dispatch Software Support</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label for="urgency">Urgency Level</label>
                            <select id="urgency">
                                <option>Standard Inquiry</option>
                                <option selected>Priority Operational Issue</option>
                                <option>Critical Terminal Stoppage</option>
                            </select>
                        </div>

                        <div class="form-group full">
                            <label for="subject">Issue Summary</label>
                            <input id="subject" type="text" value="Quay Crane 03 handover delay for Berth 03 incoming hauler convoy" required>
                        </div>

                        <div class="form-group full">
                            <label for="message">Detailed Report / Notes</label>
                            <textarea id="message" rows="3">TRK-80579 and TRK-80584 experienced a minor corridor congestion alert near Road B2. Requesting temporary route priority override for twin-lift unload.</textarea>
                        </div>

                    </div>

                    <button class="btn" type="submit">
                        Transmit Operations Dispatch
                    </button>
                </form>
            </div>

            <div class="panel">
                <h2 class="panel-title">Duty Command Directory</h2>

                <?php foreach ($contacts as $contact): ?>
                    <div class="alert-item">
                        <div class="alert-title <?php echo htmlspecialchars($contact['class']); ?>">
                            <?php echo htmlspecialchars($contact['role']); ?>
                        </div>
                        <div class="alert-text">
                            <strong>Location:</strong> <?php echo htmlspecialchars($contact['station']); ?><br>
                            <strong>Contact:</strong> <?php echo htmlspecialchars($contact['ext']); ?>
                        </div>
                    </div>
                <?php endforeach; ?>

                <div class="alert-item" style="border-top: 1px solid #edf0f2; margin-top: 12px; padding-top: 16px;">
                    <div class="alert-title green">Automated Radio Dispatch</div>
                    <div class="alert-text">
                        Digital trunked radio repeater systems operating with 99.9% uptime across all terminal zones.
                    </div>
                </div>
            </div>

        </section>

    </div>
</main>

<?php include 'footer.php'; ?>

<script>
function submitInquiry() {
    const name = document.getElementById("operatorName").value;
    const dept = document.getElementById("department").value;
    alert("Dispatch notification sent by " + name + " for " + dept + ".\nCommand center notified.");
}
</script>
