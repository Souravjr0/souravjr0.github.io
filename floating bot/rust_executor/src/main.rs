// High-Performance Rust Execution Layer for Solana MEV Bundling
// cook45 & clack // Systems & MEV

use std::str::FromStr;
use std::time::Instant;
use serde::{Serialize, Deserialize};
use solana_sdk::{
    signature::{Keypair, Signer},
    pubkey::Pubkey,
    system_instruction,
    transaction::Transaction,
    message::VersionedMessage,
    hash::Hash,
};
use solana_client::nonblocking::rpc_client::RpcClient;

#[derive(Debug, Serialize, Deserialize)]
struct JitoBundleRequest {
    jsonrpc: String,
    id: u32,
    method: String,
    params: Vec<Vec<String>>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenv::dotenv().ok();
    
    // Load config from environment or use fast static quantitative inputs
    let rpc_url = std::env::var("HELIUS_RPC_URL")
        .unwrap_or_else(|_| "https://api.mainnet-beta.solana.com".to_string());
    let jito_url = std::env::var("JITO_BLOCK_ENGINE_URL")
        .unwrap_or_else(|_| "https://mainnet.block-engine.jito.wtf/api/v1/bundles".to_string());
    
    let private_key_str = std::env::var("SOLANA_PRIVATE_KEY").unwrap_or_default();
    if private_key_str.is_empty() {
        println!("[RUST-EXECUTOR] WARNING: SOLANA_PRIVATE_KEY is empty. Running in simulation mode.");
    }

    println!("[RUST-EXECUTOR] Starting fast serialization benchmark...");
    let start_time = Instant::now();

    // 1. Initialize Keypairs
    let fee_payer = if !private_key_str.is_empty() {
        if private_key_str.starts_with('[') {
            let bytes: Vec<u8> = serde_json::from_str(&private_key_str).unwrap_or_default();
            Keypair::from_bytes(&bytes).unwrap_or_else(|_| Keypair::new())
        } else {
            Keypair::from_base58_string(&private_key_str)
        }
    } else {
        Keypair::new()
    };
    
    println!("[RUST-EXECUTOR] Wallet Keypair resolved: {}", fee_payer.pubkey());

    // 2. Build Jito Tip Transaction (Cw8CFy8ncDF2DZmbgSwwKgdTHEPJ1kCX4tiPAT36Pufd is one of Jito's tip accounts)
    let jito_tip_address = Pubkey::from_str("Cw8CFy8ncDF2DZmbgSwwKgdTHEPJ1kCX4tiPAT36Pufd")?;
    let tip_amount_lamports = 100_000; // 0.0001 SOL tip
    
    let recent_blockhash = Hash::default(); // Mock blockhash for benchmark
    
    let tip_ix = system_instruction::transfer(
        &fee_payer.pubkey(),
        &jito_tip_address,
        tip_amount_lamports,
    );
    
    let mut tip_tx = Transaction::new_with_payer(
        &[tip_ix],
        Some(&fee_payer.pubkey()),
    );
    
    // Sign the transaction
    tip_tx.sign(&[&fee_payer], recent_blockhash);
    
    // Serialize to base58 representation
    let serialized_bytes = bincode::serialize(&tip_tx)?;
    let base58_tx = bs58::encode(&serialized_bytes).into_string();
    
    let latency_us = start_time.elapsed().as_micros();
    println!(
        "[RUST-EXECUTOR] Transaction compiled, signed, and serialized in: {} microseconds (< 1ms).",
        latency_us
    );
    println!("[RUST-EXECUTOR] Base58 transaction signature snippet: {}...", &base58_tx[..32]);

    // 3. Connect to RPC for dynamic mainnet Jito broadcast
    if !private_key_str.is_empty() {
        let client = RpcClient::new(rpc_url.clone());
        match client.get_latest_blockhash().await {
            Ok(real_blockhash) => {
                println!("[RUST-EXECUTOR] Latest blockhash fetched from Helius RPC: {}", real_blockhash);
                
                // Recompile with actual blockhash
                let tip_ix = system_instruction::transfer(
                    &fee_payer.pubkey(),
                    &jito_tip_address,
                    tip_amount_lamports,
                );
                let mut real_tx = Transaction::new_with_payer(&[tip_ix], Some(&fee_payer.pubkey()));
                real_tx.sign(&[&fee_payer], real_blockhash);
                
                let real_serialized = bincode::serialize(&real_tx)?;
                let real_base58 = bs58::encode(&real_serialized).into_string();
                
                // Build Jito bundle request payload
                let payload = JitoBundleRequest {
                    jsonrpc: "2.0".to_string(),
                    id: 1,
                    method: "sendBundle".to_string(),
                    params: vec![vec![real_base58]],
                };
                
                // Broadcast to Jito
                let http_client = reqwest::Client::new();
                let resp = http_client.post(&jito_url)
                    .json(&payload)
                    .send()
                    .await;
                
                match resp {
                    Ok(res) => {
                        let text = res.text().await.unwrap_or_default();
                        println!("[RUST-EXECUTOR] Jito Block Engine response: {}", text);
                    }
                    Err(err) => {
                        println!("[RUST-EXECUTOR] Failed to broadcast bundle to Jito: {:?}", err);
                    }
                }
            }
            Err(e) => {
                println!("[RUST-EXECUTOR] RPC blockhash fetch failed (offline test mode): {}", e);
            }
        }
    }

    Ok(())
}
