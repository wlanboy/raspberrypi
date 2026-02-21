#sudo apt install git build-essential meson ninja-build pkg-config libdrm-dev libpciaccess-dev

# from https://github.com/intel/compute-runtime/releases
mkdir neo
cd neo
get https://github.com/intel/intel-graphics-compiler/releases/download/v2.28.4/intel-igc-core-2_2.28.4+20760_amd64.deb
wget https://github.com/intel/intel-graphics-compiler/releases/download/v2.28.4/intel-igc-opencl-2_2.28.4+20760_amd64.deb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/intel-ocloc-dbgsym_26.05.37020.3-0_amd64.ddeb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/intel-ocloc_26.05.37020.3-0_amd64.deb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/intel-opencl-icd-dbgsym_26.05.37020.3-0_amd64.ddeb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/intel-opencl-icd_26.05.37020.3-0_amd64.deb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/libigdgmm12_22.9.0_amd64.deb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/libze-intel-gpu1-dbgsym_26.05.37020.3-0_amd64.ddeb
wget https://github.com/intel/compute-runtime/releases/download/26.05.37020.3/libze-intel-gpu1_26.05.37020.3-0_amd64.deb
wget https://github.com/intel/intel-graphics-compiler/releases/download/v2.28.4/intel-igc-core-2_2.28.4+20760_amd64.deb
sudo apt install ocl-icd-libopencl1
sudo apt remove intel-opencl-icd intel-level-zero-gpu level-zero
# Optional: Auch die alten IGC Pakete, falls vorhanden
sudo apt remove intel-igc-core intel-igc-opencl
# Alte libigdgmm, falls vorhanden
sudo apt remove libigdgmm12
sudo dpkg -i *.deb