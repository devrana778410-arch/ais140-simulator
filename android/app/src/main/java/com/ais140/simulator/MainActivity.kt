package com.ais140.simulator
import java.util.Locale

import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.ServiceConnection
import android.graphics.Color
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
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentActivity
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import androidx.viewpager2.adapter.FragmentStateAdapter
import com.ais140.simulator.databinding.ActivityMainBinding
import com.ais140.simulator.databinding.FragmentConfigBinding
import com.ais140.simulator.databinding.FragmentLogsBinding
import com.google.android.material.snackbar.Snackbar
import com.google.android.material.tabs.TabLayoutMediator

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

    private fun setupTabs() {
        val adapter = TabAdapter(this)
        binding.viewPager.adapter = adapter
        TabLayoutMediator(binding.tabLayout, binding.viewPager) { tab, pos ->
            tab.text = if (pos == 0) "SIMULATOR" else "SOCKET LOGS"
        }.attach()
    }

    fun updateStatusChip(status: String, packets: Int) {
        val chip = binding.chipStatus
        val countTv = binding.tvPacketCount
        chip.text = status.uppercase()
        countTv.text = "TX: $packets"

        when (status) {
            SimulatorService.STATUS_SENDING, SimulatorService.STATUS_CONNECTED -> {
                chip.setChipBackgroundColorResource(R.color.success)
                chip.setTextColor(ContextCompat.getColor(this, R.color.text_primary))
            }
            SimulatorService.STATUS_CONNECTING -> {
                chip.setChipBackgroundColorResource(R.color.warning)
                chip.setTextColor(ContextCompat.getColor(this, R.color.bg_app))
            }
            SimulatorService.STATUS_ERROR -> {
                chip.setChipBackgroundColorResource(R.color.danger)
                chip.setTextColor(ContextCompat.getColor(this, R.color.text_primary))
            }
            else -> {
                chip.setChipBackgroundColorResource(R.color.stopped)
                chip.setTextColor(ContextCompat.getColor(this, R.color.text_primary))
            }
        }

        val cfg = supportFragmentManager.fragments.filterIsInstance<ConfigFragment>().firstOrNull()
        cfg?.updateRunningState(status == SimulatorService.STATUS_SENDING || status == SimulatorService.STATUS_CONNECTING)
    }

    fun appendLog(message: String) {
        logBuffer.append(message).append("\n\n")
        val fragment = supportFragmentManager.fragments.filterIsInstance<LogsFragment>().firstOrNull()
        fragment?.appendLog(message)
    }

    fun getLogBuffer(): String = logBuffer.toString()
    fun getService(): SimulatorService.SimulatorBinder? = simulatorService
    fun showSnack(msg: String) {
        Snackbar.make(binding.root, msg, Snackbar.LENGTH_SHORT).show()
    }

    private fun startAndBindService() {
        val intent = Intent(this, SimulatorService::class.java)
        ContextCompat.startForegroundService(this, intent)
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
}

class TabAdapter(fa: FragmentActivity) : FragmentStateAdapter(fa) {
    override fun getItemCount() = 2
    override fun createFragment(position: Int): Fragment =
        if (position == 0) ConfigFragment() else LogsFragment()
}

class ConfigFragment : Fragment() {

    private var _binding: FragmentConfigBinding? = null
    private val binding get() = _binding!!
    private var currentProfile = "VLTD"
    private var isSimRunning = false

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentConfigBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        setupProfileButtons()
        setupActions()
        (activity as? MainActivity)?.pendingCoordinates?.let { coords ->
            setCoordinates(coords.first, coords.second)
        }
    }

    fun setCoordinates(lat: Double, lon: Double) {
        if (_binding != null) {
            binding.etLat.setText(String.format(Locale.US, "%.6f", lat))
            binding.etLon.setText(String.format(Locale.US, "%.6f", lon))
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    private fun setupProfileButtons() {
        val accentColor = ContextCompat.getColor(requireContext(), R.color.text_accent)
        val borderColor = ContextCompat.getColor(requireContext(), R.color.border_color)
        val primaryText = ContextCompat.getColor(requireContext(), R.color.text_primary)
        val secondaryText = ContextCompat.getColor(requireContext(), R.color.text_secondary)

        fun selectProfile(profile: String) {
            currentProfile = profile
            binding.btnProfileVltd.strokeColor = android.content.res.ColorStateList.valueOf(if (profile == "VLTD") accentColor else borderColor)
            binding.btnProfileVltd.setTextColor(if (profile == "VLTD") primaryText else secondaryText)

            binding.btnProfileGpcb.strokeColor = android.content.res.ColorStateList.valueOf(if (profile == "GPCB") accentColor else borderColor)
            binding.btnProfileGpcb.setTextColor(if (profile == "GPCB") primaryText else secondaryText)

            binding.btnProfileCgm.strokeColor = android.content.res.ColorStateList.valueOf(if (profile == "CGM") accentColor else borderColor)
            binding.btnProfileCgm.setTextColor(if (profile == "CGM") primaryText else secondaryText)

            when (profile) {
                "VLTD" -> {
                    binding.etHost.setText("commonlayer.parivahan.gov.in")
                    binding.etPort.setText("9031")
                    binding.sosButtonRow.visibility = View.VISIBLE
                    binding.vregGroup.visibility = View.GONE
                }
                "GPCB" -> {
                    binding.etHost.setText("103.234.162.31")
                    binding.etPort.setText("9999")
                    binding.sosButtonRow.visibility = View.GONE
                    binding.vregGroup.visibility = View.VISIBLE
                }
                "CGM" -> {
                    binding.etHost.setText("103.234.162.150")
                    binding.etPort.setText("5013")
                    binding.sosButtonRow.visibility = View.GONE
                    binding.vregGroup.visibility = View.GONE
                }
            }
        }

        binding.btnProfileVltd.setOnClickListener { selectProfile("VLTD") }
        binding.btnProfileGpcb.setOnClickListener { selectProfile("GPCB") }
        binding.btnProfileCgm.setOnClickListener { selectProfile("CGM") }
    }

    private fun buildConfig(): PacketConfig {
        return PacketConfig(
            profile = currentProfile,
            imei = binding.etImei.text.toString().trim(),
            vehicleReg = binding.etVehicleReg.text.toString().trim(),
            latitude = binding.etLat.text.toString().toDoubleOrNull() ?: 21.705100,
            longitude = binding.etLon.text.toString().toDoubleOrNull() ?: 72.995900
        )
    }

    fun updateRunningState(running: Boolean) {
        if (_binding == null) return
        isSimRunning = running
        if (running) {
            binding.btnStartStop.text = "⏹ STOP SIMULATOR"
            binding.btnStartStop.setBackgroundColor(ContextCompat.getColor(requireContext(), R.color.danger))
            binding.btnSosOn.isEnabled = true
            binding.btnSosOff.isEnabled = true
        } else {
            binding.btnStartStop.text = "▶ START SIMULATOR"
            binding.btnStartStop.setBackgroundColor(ContextCompat.getColor(requireContext(), R.color.success))
            binding.btnSosOn.isEnabled = false
            binding.btnSosOff.isEnabled = false
        }
    }

    private fun setupActions() {
        binding.btnStartStop.setOnClickListener {
            val svc = (activity as? MainActivity)?.getService()
            if (svc == null) {
                (activity as? MainActivity)?.showSnack("Service initializing...")
                return@setOnClickListener
            }

            if (isSimRunning) {
                svc.stopSimulation()
                updateRunningState(false)
            } else {
                val config = buildConfig()
                svc.updateConfig(config)
                val host = binding.etHost.text.toString().trim()
                val port = binding.etPort.text.toString().toIntOrNull() ?: 9031
                val intervalSec = binding.etInterval.text.toString().toLongOrNull() ?: 10L
                svc.startSimulation(host, port, intervalSec * 1000L)
                updateRunningState(true)
            }
        }

        binding.btnSosOn.setOnClickListener {
            (activity as? MainActivity)?.getService()?.triggerSos("EMR")
            (activity as? MainActivity)?.showSnack("🚨 SOS ON sent!")
        }

        binding.btnSosOff.setOnClickListener {
            (activity as? MainActivity)?.getService()?.triggerSos("SEM")
            (activity as? MainActivity)?.showSnack("🛡️ SOS OFF sent!")
        }

        binding.btnPushLgn.setOnClickListener {
            val svc = (activity as? MainActivity)?.getService()
            svc?.updateConfig(buildConfig())
            svc?.sendSinglePacket("LGN")
        }

        binding.btnPushHel.setOnClickListener {
            val svc = (activity as? MainActivity)?.getService()
            svc?.updateConfig(buildConfig())
            svc?.sendSinglePacket("HEL")
        }

        binding.btnPushPvt.setOnClickListener {
            val svc = (activity as? MainActivity)?.getService()
            svc?.updateConfig(buildConfig())
            svc?.sendSinglePacket("PVT")
        }

        binding.btnExtractLink.setOnClickListener {
            val raw = binding.etLocationLink.text.toString().trim()
            if (raw.isEmpty()) {
                binding.tvLinkStatus.text = "⚠️ Please paste a link first."
                binding.tvLinkStatus.setTextColor(ContextCompat.getColor(requireContext(), R.color.warning))
                return@setOnClickListener
            }
            val coords = GeoLinkParser.extractCoordinates(raw)
            if (coords != null) {
                setCoordinates(coords.first, coords.second)
                binding.tvLinkStatus.text = String.format(Locale.US, "✅ Extracted: %.6f, %.6f", coords.first, coords.second)
                binding.tvLinkStatus.setTextColor(ContextCompat.getColor(requireContext(), R.color.success))
            } else {
                binding.tvLinkStatus.text = "❌ Failed to extract coordinates from link."
                binding.tvLinkStatus.setTextColor(ContextCompat.getColor(requireContext(), R.color.danger))
            }
        }
    }
}

class LogsFragment : Fragment() {
    private var _binding: FragmentLogsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentLogsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
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
            message.startsWith("TX") || message.startsWith("📤") || message.contains("LGN") -> Color.parseColor("#38BDF8")
            message.startsWith("✅") || message.contains("Connected") -> Color.parseColor("#34D399")
            message.startsWith("❌") || message.contains("failed") -> Color.parseColor("#F87171")
            message.startsWith("⏳") || message.startsWith("⚠️") -> Color.parseColor("#FBBF24")
            else -> Color.parseColor("#94A3B8")
        }
        val spannable = SpannableString("$message\n\n")
        spannable.setSpan(ForegroundColorSpan(color), 0, message.length, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
        binding.tvLogs.append(spannable)
        binding.scrollLogs.post {
            binding.scrollLogs.fullScroll(ScrollView.FOCUS_DOWN)
        }
    }
}
