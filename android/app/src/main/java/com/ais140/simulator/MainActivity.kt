package com.ais140.simulator

import android.app.ActivityManager
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.ServiceConnection
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.text.Spannable
import android.text.SpannableString
import android.text.style.ForegroundColorSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentActivity
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import androidx.viewpager2.adapter.FragmentStateAdapter
import com.google.android.material.chip.Chip
import com.google.android.material.snackbar.Snackbar
import com.google.android.material.tabs.TabLayoutMediator
import com.ais140.simulator.databinding.ActivityMainBinding
import com.ais140.simulator.databinding.FragmentConfigBinding
import com.ais140.simulator.databinding.FragmentLogsBinding

// ──────────────────────────── MainActivity ─────────────────────────────────

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    var pendingCoordinates: Pair<Double, Double>? = null

    private var simulatorService: SimulatorService.SimulatorBinder? = null
    private var isBound = false

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, service: IBinder) {
            simulatorService = service as SimulatorService.SimulatorBinder
            isBound = true
            appendLog("Service bound successfully")
        }

        override fun onServiceDisconnected(name: ComponentName) {
            simulatorService = null
            isBound = false
        }
    }

    // Broadcast receivers
    private val logReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val msg = intent.getStringExtra(SimulatorService.EXTRA_LOG_MSG) ?: return
            appendLog(msg)
        }
    }

    private val statusReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val status = intent.getStringExtra(SimulatorService.EXTRA_STATUS) ?: return
            val packets = intent.getIntExtra(SimulatorService.EXTRA_PACKETS_SENT, 0)
            updateStatusChip(status, packets)
        }
    }

    private var logBuffer = StringBuilder()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupTabs()
        setupStatusChip()
        startAndBindService()
        registerReceivers()
        handleIncomingIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIncomingIntent(intent)
    }

    private fun handleIncomingIntent(intent: Intent?) {
        if (intent == null) return
        var rawText: String? = null

        if (Intent.ACTION_VIEW == intent.action) {
            rawText = intent.dataString
        } else if (Intent.ACTION_SEND == intent.action && intent.type == "text/plain") {
            rawText = intent.getStringExtra(Intent.EXTRA_TEXT)
        }

        if (!rawText.isNullOrBlank()) {
            val coords = GeoLinkParser.extractCoordinates(rawText)
            if (coords != null) {
                pendingCoordinates = coords
                binding.viewPager.currentItem = 0
                val cfg = supportFragmentManager.fragments
                    .filterIsInstance<ConfigFragment>()
                    .firstOrNull()
                cfg?.setCoordinates(coords.first, coords.second)
                showSnack("📍 Location Extracted: ${coords.first}, ${coords.second}")
                appendLog("[GEO] Loaded GPS from link: ${coords.first}, ${coords.second}")
            }
        }
    }

    override fun onDestroy() {
        unregisterReceivers()
        if (isBound) unbindService(serviceConnection)
        super.onDestroy()
    }

    // ──────────────────────────── Setup ────────────────────────────────

    private fun setupTabs() {
        val adapter = TabAdapter(this)
        binding.viewPager.adapter = adapter
        TabLayoutMediator(binding.tabLayout, binding.viewPager) { tab, pos ->
            tab.text = if (pos == 0) "CONFIG" else "LOGS"
        }.attach()
    }

    private fun setupStatusChip() {
        updateStatusChip(SimulatorService.STATUS_DISCONNECTED, 0)
    }

    private fun startAndBindService() {
        val intent = Intent(this, SimulatorService::class.java)
        startForegroundService(intent)
        bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
    }

    private fun registerReceivers() {
        val lbm = LocalBroadcastManager.getInstance(this)
        lbm.registerReceiver(logReceiver, IntentFilter(SimulatorService.ACTION_LOG))
        lbm.registerReceiver(statusReceiver, IntentFilter(SimulatorService.ACTION_STATUS))
    }

    private fun unregisterReceivers() {
        val lbm = LocalBroadcastManager.getInstance(this)
        lbm.unregisterReceiver(logReceiver)
        lbm.unregisterReceiver(statusReceiver)
    }

    // ──────────────────────────── Status Chip ──────────────────────────

    fun updateStatusChip(status: String, packets: Int) {
        val chip = binding.chipStatus
        val countTv = binding.tvPacketCount
        chip.text = status
        countTv.text = "Packets: $packets"
        when (status) {
            SimulatorService.STATUS_CONNECTED -> {
                chip.setChipBackgroundColorResource(com.google.android.material.R.color.design_default_color_primary)
                chip.setTextColor(Color.WHITE)
            }
            SimulatorService.STATUS_CONNECTING -> {
                chip.setChipBackgroundColorResource(android.R.color.holo_orange_light)
                chip.setTextColor(Color.WHITE)
            }
            SimulatorService.STATUS_ERROR -> {
                chip.setChipBackgroundColorResource(android.R.color.holo_red_light)
                chip.setTextColor(Color.WHITE)
            }
            else -> {
                chip.setChipBackgroundColorResource(android.R.color.darker_gray)
                chip.setTextColor(Color.WHITE)
            }
        }
    }

    // ──────────────────────────── Logging ──────────────────────────────

    fun appendLog(message: String) {
        logBuffer.append(message).append("\n\n")
        // Notify logs fragment if visible
        val fragment = supportFragmentManager.fragments
            .filterIsInstance<LogsFragment>()
            .firstOrNull()
        fragment?.appendLog(message)
    }

    fun getLogBuffer(): String = logBuffer.toString()

    // ──────────────────────────── Service Delegation ───────────────────

    fun getService(): SimulatorService.SimulatorBinder? = simulatorService

    fun showSnack(msg: String) {
        Snackbar.make(binding.root, msg, Snackbar.LENGTH_SHORT).show()
    }
}

// ──────────────────────────── ViewPager Adapter ────────────────────────────

class TabAdapter(fa: FragmentActivity) : FragmentStateAdapter(fa) {
    override fun getItemCount() = 2
    override fun createFragment(position: Int): Fragment =
        if (position == 0) ConfigFragment() else LogsFragment()
}

// ──────────────────────────── Config Fragment ──────────────────────────────

class ConfigFragment : Fragment() {

    private var _binding: FragmentConfigBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentConfigBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        populateDefaults()
        (activity as? MainActivity)?.pendingCoordinates?.let { coords ->
            setCoordinates(coords.first, coords.second)
        }
        setupButtons()
        updatePacketPreview()
    }

    fun setCoordinates(lat: Double, lon: Double) {
        if (_binding != null) {
            binding.etLat.setText(String.format(java.util.Locale.US, "%.6f", lat))
            binding.etLon.setText(String.format(java.util.Locale.US, "%.6f", lon))
            updatePacketPreview()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    private fun populateDefaults() {
        binding.etHost.setText("commonlayer.parivahan.gov.in")
        binding.etPort.setText("9031")
        binding.etImei.setText("869833088601301")
        binding.etVehicleReg.setText("GJ01AC0000")
        binding.etHmacKey.setText("")
        binding.etInterval.setText("10")
        binding.etLat.setText("21.866640")
        binding.etLon.setText("73.183047")
        binding.etAlt.setText("46.0")
        binding.etSpeed.setText("0.0")
        binding.etHeading.setText("208.53")
        binding.etSatellites.setText("13")
        binding.etOperator.setText("AIRTEL")
        binding.etMcc.setText("404")
        binding.etMnc.setText("05")
        binding.etCellId.setText("16D5")
        binding.etLac.setText("56C5")
    }

    private fun buildConfig(): PacketConfig {
        return PacketConfig(
            imei = binding.etImei.text.toString().trim(),
            vehicleReg = binding.etVehicleReg.text.toString().trim(),
            hmacKey = binding.etHmacKey.text.toString().trim(),
            latitude = binding.etLat.text.toString().toDoubleOrNull() ?: 21.726307,
            longitude = binding.etLon.text.toString().toDoubleOrNull() ?: 73.290024,
            altitude = binding.etAlt.text.toString().toDoubleOrNull() ?: 46.0,
            speed = binding.etSpeed.text.toString().toDoubleOrNull() ?: 0.0,
            heading = binding.etHeading.text.toString().toDoubleOrNull() ?: 208.53,
            satellites = binding.etSatellites.text.toString().toIntOrNull() ?: 13,
            operator = binding.etOperator.text.toString().trim(),
            mcc = binding.etMcc.text.toString().trim(),
            mnc = binding.etMnc.text.toString().trim(),
            cellId = binding.etCellId.text.toString().trim(),
            lac = binding.etLac.text.toString().trim()
        )
    }

    private fun updatePacketPreview() {
        try {
            val config = buildConfig()
            val preview = Ais140Packet.buildPositionPacket(config)
            binding.tvPacketPreview.text = preview
        } catch (e: Exception) {
            binding.tvPacketPreview.text = "Error building packet: ${e.message}"
        }
    }

    private fun pushConfigToService() {
        val config = buildConfig()
        (activity as? MainActivity)?.getService()?.updateConfig(config)
        updatePacketPreview()
    }

    private fun setupButtons() {
        binding.btnConnect.setOnClickListener {
            pushConfigToService()
            val host = binding.etHost.text.toString().trim()
            val port = binding.etPort.text.toString().toIntOrNull() ?: 5000
            if (host.isEmpty()) {
                (activity as? MainActivity)?.showSnack("Please enter a server host")
                return@setOnClickListener
            }
            val svc = (activity as? MainActivity)?.getService()
            if (svc == null) {
                (activity as? MainActivity)?.showSnack("Service not ready")
                return@setOnClickListener
            }
            svc.connect(host, port)
            svc.sendLogin()
            (activity as? MainActivity)?.showSnack("Connecting to $host:$port…")
        }

        binding.btnDisconnect.setOnClickListener {
            (activity as? MainActivity)?.getService()?.disconnect()
            (activity as? MainActivity)?.showSnack("Disconnecting…")
        }

        binding.btnSendNow.setOnClickListener {
            pushConfigToService()
            val svc = (activity as? MainActivity)?.getService()
            if (svc?.isConnected() == true) {
                svc.sendPacketNow()
                (activity as? MainActivity)?.showSnack("Packet sent!")
            } else {
                (activity as? MainActivity)?.showSnack("Not connected!")
            }
        }

        binding.btnStartAuto.setOnClickListener {
            pushConfigToService()
            val intervalSec = binding.etInterval.text.toString().toLongOrNull() ?: 10L
            val svc = (activity as? MainActivity)?.getService()
            if (svc?.isConnected() == true) {
                svc.startAutoSend(intervalSec * 1000L)
                (activity as? MainActivity)?.showSnack("Auto-send started (${intervalSec}s interval)")
            } else {
                (activity as? MainActivity)?.showSnack("Not connected!")
            }
        }

        binding.btnStopAuto.setOnClickListener {
            (activity as? MainActivity)?.getService()?.stopAutoSend()
            (activity as? MainActivity)?.showSnack("Auto-send stopped")
        }

        binding.btnPreview.setOnClickListener {
            updatePacketPreview()
        }
    }
}

// ──────────────────────────── Logs Fragment ────────────────────────────────

class LogsFragment : Fragment() {

    private var _binding: FragmentLogsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentLogsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        // Load buffered logs
        val existing = (activity as? MainActivity)?.getLogBuffer() ?: ""
        if (existing.isNotEmpty()) {
            binding.tvLogs.text = existing
        }
        binding.btnClearLogs.setOnClickListener {
            binding.tvLogs.text = ""
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    fun appendLog(message: String) {
        if (_binding == null) return
        val color = when {
            message.startsWith("✅") || message.startsWith("📤") -> Color.parseColor("#4CAF50")
            message.startsWith("❌") || message.startsWith("⚠️") -> Color.parseColor("#F44336")
            message.startsWith("⏳") || message.startsWith("🔄") -> Color.parseColor("#FF9800")
            message.startsWith("🔌") -> Color.parseColor("#9E9E9E")
            else -> Color.parseColor("#2196F3")
        }
        val spannable = SpannableString("$message\n\n")
        spannable.setSpan(
            ForegroundColorSpan(color), 0, message.length,
            Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
        )
        binding.tvLogs.append(spannable)
        // Auto-scroll
        binding.scrollLogs.post {
            binding.scrollLogs.fullScroll(ScrollView.FOCUS_DOWN)
        }
    }
}
