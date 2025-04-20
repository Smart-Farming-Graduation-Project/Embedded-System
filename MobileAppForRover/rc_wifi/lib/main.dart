import 'package:flutter/material.dart';
import 'dart:io';
import 'dart:async'; // For Timer

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'RC Car Control',
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF121212), // Very dark gray background
        appBarTheme: const AppBarTheme(
          color: Color(0xFF1A3C34), // Deep teal for app bar
          elevation: 4,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFFFFB300), // Amber for buttons (Connect, Set Speed)
            foregroundColor: const Color(0xFFE0E0E0), // Off-white text
            padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
            textStyle: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          ),
        ),
        textTheme: const TextTheme(
          bodyLarge: TextStyle(color: Color(0xFFE0E0E0)), // Off-white text
          bodyMedium: TextStyle(color: Color(0xFFE0E0E0)),
          titleLarge: TextStyle(color: Color(0xFFE0E0E0), fontSize: 28, fontWeight: FontWeight.bold),
          labelLarge: TextStyle(color: Color(0xFFE0E0E0), fontSize: 26),
        ),
        sliderTheme: const SliderThemeData(
          activeTrackColor: Color(0xFFFFB300), // Amber for active slider track
          inactiveTrackColor: Color(0xFF78909C), // Muted gray for inactive track
          thumbColor: Color(0xFFFFB300), // Amber for slider thumb
          overlayColor: Color(0x33FFB300), // Amber overlay with transparency
        ),
        inputDecorationTheme: const InputDecorationTheme(
          labelStyle: TextStyle(color: Color(0xFFE0E0E0), fontSize: 26),
          enabledBorder: OutlineInputBorder(
            borderSide: BorderSide(color: Color(0xFFB0BEC5)), // Muted gray border
          ),
          focusedBorder: OutlineInputBorder(
            borderSide: BorderSide(color: Color(0xFFFFB300)), // Amber border when focused
          ),
        ),
      ),
      home: const ConnectionScreen(),
    );
  }
}

class ConnectionScreen extends StatefulWidget {
  const ConnectionScreen({super.key});

  @override
  _ConnectionScreenState createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  final TextEditingController _ipController = TextEditingController(text: '192.168.4.1');
  final TextEditingController _portController = TextEditingController(text: '8080');
  bool _isConnecting = false;

  Future<void> _connect() async {
    setState(() {
      _isConnecting = true;
    });
    try {
      String ip = _ipController.text;
      int port = int.parse(_portController.text);
      Socket socket = await Socket.connect(ip, port, timeout: const Duration(seconds: 10));
      Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => ControlScreen(socket: socket)),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to connect: $e'),
          backgroundColor: const Color(0xFFEF5350), // Muted red for error
        ),
      );
    } finally {
      setState(() {
        _isConnecting = false;
      });
    }
  }

  @override
  void dispose() {
    _ipController.dispose();
    _portController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'RC Car Control',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'WiFi Access Point',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 34),
            TextField(
              controller: _ipController,
              decoration: const InputDecoration(
                labelText: 'IP Address',
                border: OutlineInputBorder(),
              ),
              style: const TextStyle(fontSize: 22, color: Color(0xFFE0E0E0)),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
            const SizedBox(height: 26),
            TextField(
              controller: _portController,
              decoration: const InputDecoration(
                labelText: 'Port Number',
                border: OutlineInputBorder(),
              ),
              style: const TextStyle(fontSize: 22, color: Color(0xFFE0E0E0)),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 40),
            ElevatedButton(
              onPressed: _isConnecting ? null : _connect,
              child: _isConnecting
                  ? const CircularProgressIndicator(
                      valueColor: AlwaysStoppedAnimation<Color>(Color(0xFFE0E0E0)),
                    )
                  : const Text(
                      'Connect',
                      style: TextStyle(color: Color(0xFF121212), fontSize: 24),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class ControlScreen extends StatefulWidget {
  final Socket socket;

  const ControlScreen({super.key, required this.socket});

  @override
  _ControlScreenState createState() => _ControlScreenState();
}

class _ControlScreenState extends State<ControlScreen> {
  bool isConnected = true;
  double speed = 0;
  Timer? _keepAliveTimer;

  @override
  void initState() {
    super.initState();
    _startKeepAlive();
    widget.socket.listen(
      (data) {
        print('Received data: ${String.fromCharCodes(data)}');
      },
      onError: (error) {
        disconnect();
      },
      onDone: () {
        disconnect();
      },
    );
  }

  void _startKeepAlive() {
    _keepAliveTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (isConnected) {
        try {
          widget.socket.write('K');
        } catch (e) {
          print('Error in keep-alive: $e');
          disconnect();
        }
      } else {
        timer.cancel();
      }
    });
  }

  void disconnect() {
    if (!isConnected) return; // Prevent multiple disconnect attempts
    setState(() {
      isConnected = false;
    });
    _keepAliveTimer?.cancel();
    widget.socket.close();
    Future.microtask(() => Navigator.pop(context));
  }

  void sendCommand(String command) {
    if (isConnected) {
      try {
        widget.socket.write(command);
      } catch (e) {
        print('Error sending command: $e');
        disconnect();
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Not connected'),
          backgroundColor: Color(0xFFEF5350), // Muted red for error
        ),
      );
    }
  }

  @override
  void dispose() {
    _keepAliveTimer?.cancel();
    if (isConnected) widget.socket.close(); // Only close if still connected
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false, // Prevent default back button behavior
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          disconnect(); // Custom disconnect logic
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text(
            'RC Car Control',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          actions: [
            Padding(
              padding: const EdgeInsets.all(15.0),
              child: Icon(
                Icons.circle,
                color: isConnected
                    ? const Color.fromARGB(255, 36, 233, 213) // Teal-green for connected
                    : const Color(0xFFEF5350), // Muted red for disconnected
                size: 25,
              ),
            ),
          ],
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(height: 100),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(width: 80),
                    DirectionButton(
                      icon: Icons.arrow_upward,
                      onPressed: () => sendCommand('F'),
                      onReleased: () => sendCommand('S'),
                    ),
                    const SizedBox(width: 80),
                  ],
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    DirectionButton(
                      icon: Icons.arrow_back,
                      onPressed: () => sendCommand('L'),
                      onReleased: () => sendCommand('S'),
                    ),
                    const SizedBox(width: 80),
                    DirectionButton(
                      icon: Icons.arrow_forward,
                      onPressed: () => sendCommand('R'),
                      onReleased: () => sendCommand('S'),
                    ),
                  ],
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(width: 80),
                    DirectionButton(
                      icon: Icons.arrow_downward,
                      onPressed: () => sendCommand('B'),
                      onReleased: () => sendCommand('S'),
                    ),
                    const SizedBox(width: 80),
                  ],
                ),
                const SizedBox(height: 35),
                Slider(
                  value: speed,
                  min: 0,
                  max: 5,
                  divisions: 5,
                  label: speed.round().toString(),
                  onChanged: (value) {
                    setState(() {
                      speed = value;
                    });
                  },
                ),
                const SizedBox(height: 5),
                ElevatedButton(
                  onPressed: () {
                    sendCommand(speed.round().toString());
                  },
                  child: const Text(
                    'Set Speed',
                    style: TextStyle(color: Color(0xFF121212)),
                  ),
                ),
                const SizedBox(height: 80),
                ElevatedButton(
                  onPressed: disconnect,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color.fromARGB(255, 197, 3, 0), // Muted red for Disconnect button
                    foregroundColor: const Color.fromARGB(255, 255, 255, 255), // Off-white text
                    padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                    textStyle: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  child: const Text('Disconnect'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class DirectionButton extends StatefulWidget {
  final IconData icon;
  final VoidCallback onPressed;
  final VoidCallback onReleased;

  const DirectionButton({
    super.key,
    required this.icon,
    required this.onPressed,
    required this.onReleased,
  });

  @override
  _DirectionButtonState createState() => _DirectionButtonState();
}

class _DirectionButtonState extends State<DirectionButton> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) {
        setState(() {
          _isPressed = true;
        });
        widget.onPressed();
      },
      onTapUp: (_) {
        setState(() {
          _isPressed = false;
        });
        widget.onReleased();
      },
      onTapCancel: () {
        setState(() {
          _isPressed = false;
        });
        widget.onReleased();
      },
      child: Container(
        width: 80,
        height: 80,
        decoration: BoxDecoration(
          color: _isPressed ? const Color(0xFF2E7D32) : const Color(0xFF1A3C34), // Dark teal, lighter when pressed
          borderRadius: BorderRadius.circular(25),
          boxShadow: const [
            BoxShadow(
              color: Colors.black54,
              blurRadius: 5,
              offset: Offset(2, 2),
            ),
          ],
        ),
        child: Center(
          child: Icon(
            widget.icon,
            color: const Color(0xFFE0E0E0), // Off-white icons
            size: 40,
          ),
        ),
      ),
    );
  }
}