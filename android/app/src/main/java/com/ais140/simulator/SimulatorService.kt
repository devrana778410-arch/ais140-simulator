package com.ais140.simulator

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Binder
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.InetSocketAddress
import java.net.Socket

/**
 * Background Service managing the TCP connection to Parivahan/CGM/GPCB.
 * Supports dual-port VLTD routing (port 9031 for Primary, port 9032 for Emergency).
 */
class SimulatorService : Service() {

    companion object {
        const val CHANNEL_ID = "ais140_simulator_channel"
        const val NOTIFICATION_ID = 1001

        const val ACTION_LOG = "com.ais140.simulator.ACTION_LOG"
        const val ACTION_STATUS = "com.ais140.simulator.ACTION_STATUS"
        const val EXTRA_LOG_MSG = "log_message"
        const val EXTRA_STATUS = "status"
        const val EXTRA_PACKETS_SENT = "packets_sent"

        const val STATUS_CONNECTED = "Connected"
        const val STATUS_DISCONNECTED = "Stopped"
        const val STATUS_CONNECTING = "Connecting"
        const val STATUS_SENDING = "Sending"
        const val STATUS_ERROR = "Error"
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var loopJob: Job? = null

    private var packetsSent = 0
    private var isRunning = false
    private var emergencyMode: String? = null

    var config = PacketConfig()
    var serverHost = "commonlayer.parivahan.gov.in"
    var serverPort = 9031
    var emergencyPort = 9032
    var sendIntervalMs = 10_000L

    inner class SimulatorBinder : Binder() {
        fun getService(): SimulatorService = this@SimulatorService
        fun isRunning() = this@SimulatorService.isRunning
        fun getPacketsSent() = packetsSent

        fun startSimulation(host: String, port: Int, intervalMs: Long) {
            serverHost = host
            serverPort = port
            sendIntervalMs = intervalMs
            startSimulatorLoop()
        }

        fun stopSimulation() {
            stopSimulatorLoop()
        }

        fun sendSinglePacket(packetType: String) {
            serviceScope.launch {
                sendInstantPacket(packetType)
            }
        }

        fun triggerSos(mode: String) {
            emergencyMode = mode
            serviceScope.launch {
                sendInstantPacket(mode)
            }
        }

        fun updateConfig(newConfig: PacketConfig) {
            config = newConfig
        }
    }

    private val binder = SimulatorBinder()
    override fun onBind(intent: Intent): IBinder = binder

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification("Simulator Ready"))
    }

    override fun onDestroy() {
        stopSimulatorLoop()
        serviceScope.cancel()
        super.onDestroy()
    }

    private fun startSimulatorLoop() {
        if (isRunning) return
        isRunning = true
        packetsSent = 0
        emergencyMode = null

        loopJob?.cancel()
        loopJob = serviceScope.launch {
            broadcastStatus(STATUS_CONNECTING)
            broadcastLog("🚀 Starting Simulator: $serverHost:$serverPort (Interval: ${sendIntervalMs / 1000}s)")
            updateNotification("Connecting...")

            val isVltd = config.profile == "VLTD"

            if (isVltd) {
                // Step 1: Send Login ($LGN) on connect
                broadcastLog("--- Sending Login & Health Sequence ---")
                sendInstantPacket("LGN")
                delay(1000)
                // Step 2: Send Health ($HEL) on connect
                sendInstantPacket("HEL")
                delay(1000)
            }

            broadcastStatus(STATUS_SENDING)
            var cycle = 0

            while (isActive && isRunning) {
                cycle++
                if (isVltd) {
                    // Send periodic PVT
                    sendInstantPacket("PVT")

                    // If emergency mode active, also send EMR
                    if (emergencyMode == "EMR") {
                        delay(600)
                        sendInstantPacket("EMR")
                    } else if (emergencyMode == "SEM") {
                        delay(600)
                        sendInstantPacket("SEM")
                        emergencyMode = null
                    }

                    // Periodically send HEL every 5 cycles
                    if (cycle % 5 == 0) {
                        delay(600)
                        sendInstantPacket("HEL")
                    }
                } else {
                    // CGM / GPCB position send
                    sendInstantPacket("PVT")
                }

                delay(sendIntervalMs)
            }
        }
    }

    private fun stopSimulatorLoop() {
        isRunning = false
        emergencyMode = null
        loopJob?.cancel()
        broadcastStatus(STATUS_DISCONNECTED)
        broadcastLog("⏹ Simulator Stopped.")
        updateNotification("Stopped")
    }

    /**
     * Sends an instant packet using direct socket connect-and-close pattern.
     * Prevents TCP reset (WinError 10054 / Connection reset by peer) from Parivahan server.
     */
    private suspend fun sendInstantPacket(packetType: String) = withContext(Dispatchers.IO) {
        val targetPort = if (packetType in listOf("EMR", "SEM")) emergencyPort else serverPort
        val cfg = config.copy(seqNum = packetsSent + 1)

        val packet = when (packetType) {
            "LGN" -> Ais140Packet.buildLoginPacket(cfg)
            "HEL" -> Ais140Packet.buildHealthPacket(cfg)
            "PVT" -> Ais140Packet.buildPositionPacket(cfg)
            "EMR" -> Ais140Packet.buildEmergencyPacket(cfg, mode = "EMR")
            "SEM" -> Ais140Packet.buildEmergencyPacket(cfg, mode = "SEM")
            else -> Ais140Packet.buildPositionPacket(cfg)
        }

        try {
            Socket().use { sock ->
                sock.soTimeout = 8000
                // Connect with 6s timeout
                sock.connect(InetSocketAddress(serverHost, targetPort), 6000)
                val bytes = (packet + "\r\n").toByteArray(Charsets.UTF_8)
                sock.getOutputStream().apply {
                    write(bytes)
                    flush()
                }
            }

            packetsSent++
            val preview = if (packet.length > 70) packet.substring(0, 70) + "..." else packet
            broadcastLog("TX [$packetType] -> :$targetPort: $preview")
            broadcastStatus(if (isRunning) STATUS_SENDING else STATUS_DISCONNECTED)
            updateNotification("Sent: $packetsSent packets")
        } catch (e: Exception) {
            broadcastLog("❌ Send failed [$packetType] on :$targetPort: ${e.message}")
            if (isRunning) {
                broadcastStatus(STATUS_ERROR)
            }
        }
    }

    private fun broadcastLog(message: String) {
        val intent = Intent(ACTION_LOG).apply {
            putExtra(EXTRA_LOG_MSG, message)
        }
        LocalBroadcastManager.getInstance(this).sendBroadcast(intent)
    }

    private fun broadcastStatus(status: String) {
        val intent = Intent(ACTION_STATUS).apply {
            putExtra(EXTRA_STATUS, status)
            putExtra(EXTRA_PACKETS_SENT, packetsSent)
        }
        LocalBroadcastManager.getInstance(this).sendBroadcast(intent)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AIS 140 Simulator",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "AIS-140 Background Telematics Stream"
            }
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(contentText: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AIS-140 Simulator")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_menu_send)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateNotification(contentText: String) {
        getSystemService(NotificationManager::class.java)?.notify(
            NOTIFICATION_ID,
            buildNotification(contentText)
        )
    }
}
