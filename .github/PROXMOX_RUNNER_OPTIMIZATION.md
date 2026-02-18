# Proxmox VM Optimization for GitHub Actions Runner

This guide covers Proxmox VM settings to optimize multi-arch Docker builds (especially ARM64 cross-compilation via QEMU).

## Critical Settings

### 1. CPU Configuration

**Enable Nested Virtualization (Required for QEMU)**
```bash
# On Proxmox host, edit VM config:
qm set <VMID> --cpu host,hidden=1,flags=+pdpe1gb
```

**In Proxmox Web UI:**
- `VM > Hardware > Processors`
  - **Type**: `host` (passes through host CPU features)
  - **Cores**: 8+ (recommended for parallel builds)
  - **Enable**: ☑️ NUMA, ☑️ Advanced (flags: +pdpe1gb)

### 2. Memory Settings

**Minimum**: 16 GB  
**Recommended**: 32 GB for Angular builds

```bash
qm set <VMID> --memory 32768
```

**In Proxmox Web UI:**
- `VM > Hardware > Memory`
  - **Memory**: 32768 MB (32 GB)
  - **Ballooning Device**: Disabled (ensures consistent memory)

### 3. Disk I/O Optimization

**Use VirtIO SCSI with SSD**
```bash
qm set <VMID> --scsi0 <storage>:<size>,iothread=1,discard=on,ssd=1,cache=writeback
```

**In Proxmox Web UI:**
- `VM > Hardware > Hard Disk`
  - **Bus**: VirtIO Block or SCSI (with VirtIO SCSI controller)
  - **Cache**: Write back
  - **IO thread**: Enabled
  - **Discard**: Enabled (for SSD TRIM)
  - **SSD emulation**: Enabled (if using SSD storage)

### 4. Network Configuration

**Use VirtIO Network Adapter**
```bash
qm set <VMID> --net0 virtio,bridge=vmbr0,firewall=0
```

**In Proxmox Web UI:**
- `VM > Hardware > Network Device`
  - **Model**: VirtIO (paravirtualized)
  - **Rate limit**: None
  - **Firewall**: Disabled (if handled elsewhere)

## Additional Optimizations

### 5. NUMA Configuration (for multi-socket hosts)

If your Proxmox host has multiple CPU sockets:
```bash
qm set <VMID> --numa 1
```

### 6. Huge Pages (Optional, for large memory workloads)

**On Proxmox host:**
```bash
# Add to /etc/sysctl.conf
vm.nr_hugepages = 8192

# Apply
sysctl -p
```

Then enable in VM:
```bash
qm set <VMID> --hugepages 2
```

### 7. Boot Order & BIOS

**Use OVMF (UEFI) for better performance:**
```bash
qm set <VMID> --bios ovmf
```

### 8. Machine Type

**Use latest q35 machine type:**
```bash
qm set <VMID> --machine q35
```

## Inside the VM (Guest OS)

### Install QEMU with KVM acceleration support

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y qemu-user-static qemu-system-aarch64 binfmt-support

# Verify KVM support
lsmod | grep kvm
kvm_intel          # or kvm_amd

# Verify nested virtualization
cat /sys/module/kvm_intel/parameters/nested  # Should show "Y"
# or for AMD:
cat /sys/module/kvm_amd/parameters/nested
```

### Docker Configuration

**Enable BuildKit with KVM:**
```bash
# Edit /etc/docker/daemon.json
{
  "features": {
    "buildkit": true
  },
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "20GB"
    }
  }
}

sudo systemctl restart docker
```

### Increase System Limits

```bash
# Edit /etc/security/limits.conf
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536

# Edit /etc/sysctl.conf
fs.inotify.max_user_watches=524288
fs.inotify.max_user_instances=512
vm.max_map_count=262144

# Apply
sudo sysctl -p
```

## Expected Performance

With these optimizations:

| Architecture | Build Time (Before) | Build Time (After) | Improvement |
|--------------|--------------------|--------------------|-------------|
| linux/amd64  | 3-4 minutes        | 2-3 minutes        | 25-33%      |
| linux/arm64  | 60+ minutes        | 15-20 minutes      | 66-75%      |

## Verification Commands

Run these on the runner VM to verify configuration:

```bash
# Check CPU features
lscpu | grep -E "Thread|Core|Socket|Flags"
grep -E "vmx|svm" /proc/cpuinfo  # Should show CPU virtualization support

# Check nested virtualization
cat /sys/module/kvm_*/parameters/nested

# Check available memory
free -h

# Check disk I/O scheduler
cat /sys/block/*/queue/scheduler  # Should show [mq-deadline] or [none]

# Check Docker QEMU setup
docker buildx ls
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Test cross-compilation
docker buildx build --platform linux/arm64 -t test:arm64 .
```

## Troubleshooting

### If ARM64 builds still hang:

1. **Check QEMU version**: Ensure QEMU 6.0+ is installed
   ```bash
   qemu-aarch64-static --version
   ```

2. **Verify binfmt is registered**:
   ```bash
   ls -la /proc/sys/fs/binfmt_misc/
   # Should show qemu-aarch64 entry
   ```

3. **Increase Docker memory**:
   ```bash
   # Edit /etc/docker/daemon.json
   {
     "default-ulimits": {
       "memlock": {
         "Hard": -1,
         "Name": "memlock",
         "Soft": -1
       }
     }
   }
   ```

4. **Monitor build progress**:
   ```bash
   # In another terminal
   docker stats
   htop
   iostat -x 5
   ```

## Quick Start Checklist

- [ ] CPU type set to `host`
- [ ] Nested virtualization enabled (`flags=+pdpe1gb`)
- [ ] Minimum 8 CPU cores allocated
- [ ] Minimum 32 GB RAM allocated
- [ ] VirtIO disk with SSD, iothread, and writeback cache
- [ ] VirtIO network adapter
- [ ] QEMU user-static installed in guest
- [ ] Docker BuildKit enabled
- [ ] System limits increased (nofile, nproc)
- [ ] Verified with test ARM64 build

## Apply All Settings Script

Save and run on Proxmox host:

```bash
#!/bin/bash
VMID=<YOUR_RUNNER_VMID>

echo "Applying optimizations to VM $VMID..."

qm set $VMID --cpu host,hidden=1,flags=+pdpe1gb
qm set $VMID --cores 8
qm set $VMID --memory 32768
qm set $VMID --balloon 0
qm set $VMID --numa 1
qm set $VMID --machine q35

echo "Done! Restart VM for changes to take effect:"
echo "  qm stop $VMID && qm start $VMID"
```

---

**Related Documentation:**
- [Docker Buildx Multi-platform](https://docs.docker.com/build/building/multi-platform/)
- [QEMU User Emulation](https://www.qemu.org/docs/master/user/main.html)
- [Proxmox CPU Configuration](https://pve.proxmox.com/wiki/Qemu/KVM_Virtual_Machines#qm_cpu)
