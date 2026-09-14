from src.engines.cipher_factory import CipherFactory
from src.analyzers.security_evaluator import SecurityEvaluator

class SecurityService:
    def __init__(self, factory: CipherFactory = None):
        self.factory = factory or CipherFactory()
        
    def run_security_suite(
        self, 
        configs: list[dict], 
        plaintext1: bytes, 
        plaintext2: bytes, 
        key1: bytes, 
        key2: bytes, 
        image_bytes: bytes, 
        iv: bytes
    ) -> dict:
        """
        Execute SecurityEvaluator logic over multiple configurations.
        Returns a nested dictionary of exact evaluator results.
        
        Requires the caller to explicitly supply a controlled 16-byte IV 
        for the security experiment suite.
        """
        results = {}
        for config in configs:
            cipher = self.factory.create_cipher(config["algorithm"], config["key_size"], config["mode"])
            
            conf_str = f"{config['algorithm']}-{config['key_size']}-{config['mode']}"
            conf_results = {}
            
            # ECB/CBC IV Handling Contract:
            # ECB mode must receive iv=None for standard encryptions.
            evaluator_iv = iv if config["mode"].upper() == "CBC" else None
            
            # Avalanche
            av = SecurityEvaluator.calculate_avalanche_effect(plaintext1, plaintext2, cipher, key1, evaluator_iv)
            conf_results["avalanche_effect"] = av
            
            # Key Sensitivity
            ks = SecurityEvaluator.test_key_sensitivity(cipher, plaintext1, key1, key2, evaluator_iv)
            conf_results["key_sensitivity"] = ks
                
            # ECB Weakness (Image)
            if config["mode"].upper() == "ECB":
                # The ECB weakness experiment explicitly requires the controlled IV for its CBC baseline.
                ecb_res = SecurityEvaluator.test_ecb_weakness(image_bytes, key1, iv) 
                conf_results["ecb_weakness"] = ecb_res
                    
            results[conf_str] = conf_results
            
        return results
