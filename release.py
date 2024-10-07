import os
import time
import json
from web3 import Web3
import subprocess


# Initialize web3 (assuming you are connecting to a local node)
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

INIT_GOV = '0x6f3cBE2ab3483EC4BA7B672fbdCa0E9B33F88db8'
V3_VAULT_ORIGINAL = '0xcA78AF7443f3F8FA0148b746Cb18FF67383CDF3f'
RELEASE_DATA_FILE_PATH = "./release/release_data.json"
config_file = "release_config.yaml"


def main():
    release_name = "v3.0.3"
    build_release_data(release_name)

def build_release_data(release: str):
    data = {
        "releases": {
            release: {
                "release_timestamp": int(time.time()),
                "contracts": {}
            }
        }
    }

    contracts_files = get_contract_files()
    project_type = detect_project_type()

    if project_type == 'foundry':
        compile_with_foundry()
        
    for contract_file in contracts_files:
        if project_type == 'foundry':
            print(f"Processing Foundry contract: {contract_file}")
            bytecode, abi = get_foundry_artifacts(contract_file)
        else:
            bytecode, abi = get_ape_artifacts(contract_file)

        if bytecode and abi:
            data["releases"][release]["contracts"][contract_file] = {
                "bytecode": bytecode,
                "abi": abi
            }
            print(f"Processed contract: {contract_file}")

    # Convert data to JSON and print (or save to file if needed)
    json_data = json.dumps(data, indent=2)

    save_to_file(RELEASE_DATA_FILE_PATH, json_data)

    print(f"Release data written to {RELEASE_DATA_FILE_PATH}")


def detect_project_type():
    """
    Detects the project type by checking the presence of a 'foundry.toml' file.
    Returns 'foundry' if found, otherwise returns 'vyper'.
    """
    if os.path.exists('ape-config.yaml') or os.path.exists('ape-config.yml'):
        return 'ape'
    else:
        return 'foundry'

def get_contract_files():
    """
    Searches for files with .sol or .vy extensions within the specified root directories,
    excluding any paths that are within the exclude_dir.
    Supports both './contracts' and './src' as root directories.
    Returns a list of filenames without paths.
    """
    root_directories = ['./contracts', './src']
    directories_to_exclude = [
        'contracts/.cache', 'contracts/interfaces', 'contracts/test',
        'src/.cache', 'src/interfaces', 'src/test'
    ]
    contracts = []

    for root_directory in root_directories:
        # Check if the directory exists before searching for files
        if not os.path.exists(root_directory):
            continue

        for root, dirs, files in os.walk(root_directory, topdown=True):
            # Normalize the root to simplify path handling
            normalized_root = os.path.normpath(root)
            # Filter out directories to exclude by checking the full normalized path
            dirs[:] = [d for d in dirs if os.path.normpath(os.path.join(normalized_root, d)) not in directories_to_exclude]

            for file in files:
                if file.endswith('.sol') or file.endswith('.vy'):
                    contracts.append(file)  # Append only the filename

    return contracts

def get_foundry_artifacts(contract_name):
    """
    Extracts the bytecode of the specified contract from the Foundry's artifacts.
    :param contract_name: The name of the contract (e.g., "MyContract").
    :return: The bytecode of the specified contract or None if not found.
    """
    artifacts_dir = './out'  # Foundry's default output directory
    contract_name = contract_name.replace(".sol", "")
    artifact_path = os.path.join(artifacts_dir, f"{contract_name}.sol", f"{contract_name}.json")

    # Check if the artifact JSON file exists
    if not os.path.exists(artifact_path):
        print(f"Error: Artifact for {contract_name} not found at {artifact_path}.")
        return None, None

    # Load the artifact JSON to extract the bytecode
    with open(artifact_path, 'r') as file:
        artifact = json.load(file)
        bytecode = artifact.get('bytecode', {}).get('object')
        if bytecode == '0x':
            return None, None
        abi = artifact.get('abi', [])

    if bytecode:
        print(f"Bytecode for {contract_name}: {bytecode[:40]}...")  # Print a portion of the bytecode for brevity
    else:
        print(f"No bytecode found for {contract_name}.")
    
    return bytecode, abi

def get_ape_artifacts(contract_path):
    """
    Compiles a Solidity or Vyper contract depending on the file extension.
    Returns the contract name, bytecode, and ABI.
    """
    contract_name = os.path.splitext(os.path.basename(contract_path))[0]

    if contract_path.endswith('.sol'):
        raise Exception("Solidity contracts are not supported with Ape")
    elif contract_path.endswith('.vy'):
        return compile_vyper_contract(contract_path, contract_name)
    else:
        return None, None


def compile_with_foundry():
    """
    Compiles the contracts using Foundry's forge.
    """
    print(f"Compiling Solidity contracts")
    try:
        # Run the `forge compile` command without capturing output
        result = subprocess.run(['forge', 'compile'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation: {e}")
        return False
    return True


def compile_vyper_contract(contract_path, contract_name):
    """
    Compiles a Vyper contract using the Vyper compiler.
    Returns the contract name, bytecode, and ABI.
    """
    with open(contract_path, 'r') as f:
        source_code = f.read()

    try:
        bytecode = vyper.compile_code(source_code, ['bytecode'])['bytecode']
        abi = vyper.compile_code(source_code, ['abi'])['abi']
        return bytecode, abi
    except Exception as e:
        print(f"Error compiling Vyper contract {contract_name}: {e}")
        return None, None

# Load the YAML config file
def load_config(config_file):
    with open(config_file, "r") as file:
        return yaml.safe_load(file)


def save_to_file(file_path, data):
    # Extract the directory from the file path
    directory = os.path.dirname(file_path)
    
    # If the directory does not exist, create it
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directory {directory} created.")
    
    # Write the data to the file
    with open(file_path, 'w') as file:
        file.write(data)
        print(f"File saved to {file_path}")




if __name__ == "__main__":
    main()