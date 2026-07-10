const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await ethers.getSigners();
  const Registry = await ethers.getContractFactory("AuditRegistry");
  const registry = await Registry.deploy();
  await registry.deployed();

  const artifact = await artifacts.readArtifact("AuditRegistry");
  const deployment = {
    address: registry.address,
    abi: artifact.abi,
    rpc_url: "http://127.0.0.1:8545",
    // Default Hardhat account #0. Keep this local-only for coursework demos.
    private_key: "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    deployer: deployer.address,
  };

  fs.writeFileSync(
    path.join(__dirname, "..", "deployment.json"),
    JSON.stringify(deployment, null, 2),
    "utf8"
  );
  console.log(`AuditRegistry deployed to ${registry.address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
