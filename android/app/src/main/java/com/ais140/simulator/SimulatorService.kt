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
import java.io.OutputStream
import java.net.Socket
import java.net.SocketException

/**
 * Foreground service that manages the TCP connection to an AIS 140 server
 * and sends position packets at a configurable interval.
 */
class SimulatorService : Service() {

    // ──────────────────────────── Constants ────────────────────────────

    companion object {
        const val CHANNEL_ID = "ais140_simulator_channel"
        const val NOTIFICATION_ID = 1001

        // Broadcast actions
        const val ACTION_LOG = "com.ais140.simulator.ACTION_LOG"
        const val ACTION_STATUS = "com.ais140.simulator.ACTION_STATUS"
        const val EXTRA_LOG_MSG = "log_message"
        const val EXTRA_STATUS = "status"
        const val EXTRA_PACKETS_SENT = "packets_sent"

        // Intent extras for start command
        const val EXTRA_HOST = "host"
        const val EXTRA_PORT = "port"
        const val EXTRA_INTERVAL = "interval"
        const val EXTRA_CONFIG = "config_json"

        // Status values
        const val STATUS_CONNECTED = "CONNECTED"
        const val STATUS_DISCONNECTED = "DISCONNECTED"
        const val STATUS_CONNECTING = "CONNECTING"
        const val STATUS_ERROR = "ERROR"
    }

    // ──────────────────────────── State ────────────────────────────────

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var connectionJob: Job? = null
    private var autoSendJob: Job? = null

    private var socket: Socket? = null
    private var outputStream: OutputStream? = null

    private var packetsSent = 0
    private var isConnected = false
    private var isAutoSending = false

    // Current simulation parameters (updated from MainActivity via Binder)
    var config = PacketConfig()
    var serverHost = "192.168.1.1"
    var serverPort = 5000
    var sendIntervalMs = 10_000L // 10 seconds default

    // ──────────────────────────── Binder ───────────────────────────────

    inner class SimulatorBinder : Binder() {
        fun getService(): SimulatorService = this@SimulatorService

        fun isConnected() = this@SimulatorService.isConnected
        fun isAutoSending() = this@SimulatorService.isAutoSending
        fun getPacketsSent() = packetsSent

        fun connect(host: String, port: Int) {
            serverHost = host
            serverPort = port
            startConnection()
        }

        fun disconnect() = closeConnection("User disconnected")

        fun sendPacketNow() = sendPositionPacketNow()

        fun startAutoSend(intervalMs: Long) {
            sendIntervalMs = intervalMs
            startAutoSend()
        }

        fun stopAutoSend() = this@SimulatorService.stopAutoSend()

        fun sendLogin() = sendLoginPacket()

        fun updateConfig(newConfig: PacketConfig) {
            config = newConfig
        }
    }

    private val binder = SimulatorBinder()

    override fun onBind(intent: Intent): IBinder = binder

    // ──────────────────────────── Lifecycle ────────────────────────────

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification("Idle — tap to open"))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onDestroy() {
        closeConnection("Service destroyed")
        serviceScope.cancel()
        super.onDestroy()
    }

    // ──────────────────────────── Connection ───────────────────────────

    private fun startConnection() {
        connectionJob?.cancel()
        connectionJob = serviceScope.launch {
            broadcastStatus(STATUS_CONNECTING)
            broadcastLog("⏳ Connecting to $serverHost:$serverPort …")
            updateNotification("Connecting to $serverHost:$serverPort")

            var attempt = 0
            while (isActive) {
                attempt++
                try {
                    val sock = Socket(serverHost, serverPort)
                    sock.soTimeout = 30_000
                    socket = sock
                    outputStream = sock.getOutputStream()
                    isConnected = true
                    packetsSent = 0

                    broadcastStatus(STATUS_CONNECTED)
                    broadcastLog("✅ Connected to $serverHost:$serverPort (attempt $attempt)")
                    updateNotification("Connected — 0 packets sent")

                    // Wait until socket closes externally
                    while (isActive && sock.isConnected && !sock.isClosed) {
                        delay(1_000)
                    }
                    throw SocketException("Connection closed remotely")
                } catch (e: Exception) {
                    isConnected = false
                    broadcastStatus(STATUS_ERROR)
                    broadcastLog("❌ Connection lost: ${e.message}. Retrying in 5 s…")
                    updateNotification("Reconnecting… (attempt ${attempt + 1})")
                    closeSocketSilently()
                    delay(5_000)
                }
            }
        }
    }

    private fun closeConnection(reason: String) {
        autoSendJob?.cancel()
        connectionJob?.cancel()
        isConnected = false
        isAutoSending = false
        closeSocketSilently()
        broadcastStatus(STATUS_DISCONNECTED)
        broadcastLog("🔌 Disconnected: $reason")
        updateNotification("Idle — tap to open")
    }

    private fun closeSocketSilently() {
        try { outputStream?.close() } catch (_: Exception) {}
        try { socket?.close() } catch (_: Exception) {}
        outputStream = null
        socket = null
    }

    // ──────────────────────────── Packet Sending ───────────────────────

    private fun sendLoginPacket() {
        serviceScope.launch {
            val packet = Ais140Packet.buildLoginPacket(config)
            sendRaw(packet, "LOGIN")
        }
    }

    private fun sendPositionPacketNow() {
        serviceScope.launch {
            val packet = Ais140Packet.buildPositionPacket(config)
            sendRaw(packet, "POSITION")
        }
    }

    private fun startAutoSend() {
        autoSendJob?.cancel()
        isAutoSending = true
        autoSendJob = serviceScope.launch {
            broadcastLog("🔄 Auto-send started (every ${sendIntervalMs / 1000} s)")
            while (isActive && isAutoSending) {
                if (isConnected) {
                    val packet = Ais140Packet.buildPositionPacket(config)
                    sendRaw(packet, "AUTO")
                } else {
                    broadcastLog("⚠️ Not connected — skipping packet")
                }
                delay(sendIntervalMs)
            }
        }
    }

    private fun stopAutoSend() {
        autoSendJob?.cancel()
        isAutoSending = false
        broadcastLog("⏹ Auto-send stopped")
    }

    private suspend fun sendRaw(packet: String, tag: String) = withContext(Dispatchers.IO) {
        try {
            val os = outputStream ?: throw SocketException("No output stream")
            val bytes = (packet + "\r\n").toByteArray(Charsets.UTF_8)
            os.write(bytes)
            os.flush()
            packetsSent++
            broadcastLog("📤 [$tag] Sent packet #$packetsSent:\n$packet")
            broadcastStatus(if (isConnected) STATUS_CONNECTED else STATUS_DISCONNECTED)
            updateNotification("Connected — $packetsSent packets sent")
        } catch (e: Exception) {
            broadcastLog("❌ Send failed [$tag]: ${e.message}")
            isConnected = false
            broadcastStatus(STATUS_ERROR)
            closeSocketSilently()
        }
    }

    // ──────────────────────────── Broadcasts ───────────────────────────

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

    // ──────────────────────────── Notification ─────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AIS 140 Simulator",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Persistent notification for AIS 140 simulation"
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(contentText: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AIS 140 Simulator")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_menu_send)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateNotification(contentText: String) {
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIFICATION_ID, buildNotification(contentText))
    }
}
