"""Configuration settings for Nougat processor"""

from pathlib import Path
import torch


class Config:
    """Configuration class for Nougat OCR processor"""

    # Base directories - For METIS
    # METADATA_BASE_DIR = Path("/lstr/sahara/graphlab/ratul/data/metadata/")
    # PDF_BASE_DIR = Path("/lstr/sahara/graphlab/ratul/data/papers/")
    # NOUGAT_OUTPUT_BASE = Path("/home/ratul/masterset-data-preparation/output/nougat_output")

    # Base directories - For 10.158.56.231 Server
    # METADATA_BASE_DIR = Path("/mnt/data/data/metadata/")
    # PDF_BASE_DIR = Path("/mnt/data/data/papers/")
    # NOUGAT_OUTPUT_BASE = Path("/home/ratul/masterset-recommendation/data/nougat_output")

    # Base directories - For lancer
    METADATA_BASE_DIR = Path("/home/ratul/masterset-recommendation/data/metadata/")
    PDF_BASE_DIR = Path("/home/ratul/masterset-recommendation/data/papers/")
    NOUGAT_OUTPUT_BASE = Path("/home/ratul/masterset-recommendation/data/nougat_output")

    # Marker output directory (checked during --fallback to skip marker successes)
    MARKER_OUTPUT_BASE = Path("/home/ratul/masterset-recommendation/data/marker_output")

    # Model settings
    MODEL_NAME = "facebook/nougat-small"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    # Nougat generation parameters
    MIN_LENGTH = 1
    MAX_NEW_TOKENS = 3500
    REPETITION_PENALTY = 1.2
    DPI = 96

    # Supported conferences
    CONFERENCES = [
        "aaai",
        "acl",
        "aistats",
        "colt",
        "cvpr",
        "eccv",
        "emnlp",
        "iccv",
        "iclr",
        "icml",
        "ijcai",
        "jmlr",
        "naacl",
        "neurips",
        "uai",
    ]

    # Progress tracking
    PROGRESS_FILE = "nougat_progress.json"

    # Fallback list: PDFs that GROBID failed to process (103 files)
    # These will be processed by Nougat and saved to nougat_output/{conf}/{year}/
    # Run with: python nougat.py --fallback
    FALLBACK_PDFS = [
        "data/papers/aistats/2017/poulis17a_Learning with Feature Feedback_ from Theory to Pra.pdf",
        "data/papers/aistats/2020/pan20a_Interpretable Companions for Black-Box Models.pdf",
        "data/papers/cvpr/2015/Liu_Data-Driven_Sparsity-Based_Restoration_2015_CVPR_paper_Data-Driven Sparsity-Based Restoration of JPEG-Com.pdf",
        "data/papers/cvpr/2015/Song_Joint_Multi-Feature_Spatial_2015_CVPR_paper_Joint Multi-Feature Spatial Context for Scene Reco.pdf",
        "data/papers/cvpr/2024/Chatterjee_On_the_Robustness_of_Language_Guidance_for_Low-Level_Vision_Tasks_CVPR_2024_paper_On the Robustness of Language Guidance for Low-Lev.pdf",
        "data/papers/cvpr/2025/Zhang_Weakly_Supervised_Contrastive_Adversarial_Training_for_Learning_Robust_Features_from_CVPR_2025_paper_Weakly Supervised Contrastive Adversarial Training.pdf",
        "data/papers/eccv/2024/10541_ECCV_2024_paper_Reinforcement Learning via Auxillary Task Distilla.pdf",
        "data/papers/eccv/2024/10555_ECCV_2024_paper_View-Consistent Hierarchical 3D Segmentation Using.pdf",
        "data/papers/iclr/2019/HyeVtoRqtQ_Trellis Networks for Sequence Modeling.pdf",
        "data/papers/iclr/2021/FX0vR39SJ5q_Isometric Transformation Invariant and Equivariant.pdf",
        "data/papers/iclr/2021/S0UdquAnr9k_Locally Free Weight Sharing for Network Width Sear.pdf",
        "data/papers/iclr/2023/UvmDCdSPDOW_Information-Theoretic Diffusion.pdf",
        "data/papers/iclr/2023/_BoPed4tYww_Timing is Everything_ Learning to Act Selectively .pdf",
        "data/papers/iclr/2024/QiJuMJl0QS_Efficient Heterogeneous Meta-Learning via Channel .pdf",
        "data/papers/iclr/2026/vBmRQHW7en_Sampling-aware Adversarial Attacks Against Large L.pdf",
        "data/papers/icml/2019/ma19c_EDDI_ Efficient Dynamic Discovery of High-Value In.pdf",
        "data/papers/icml/2025/wang25fd_COSDA_ Counterfactual-based Susceptibility Risk Fr.pdf",
        "data/papers/neurips/2016/2dffbc474aa176b6dc957938c15d0c8b_Regret Bounds for Non-decomposable Metrics with Mi.pdf",
        "data/papers/neurips/2017/019d385eb67632a7e958e23f24bd07d7_Langevin Dynamics with Continuous Tempering for Tr.pdf",
        "data/papers/neurips/2019/5cde6dedeb8892e3794f22db57ada073_A Unified Framework for Data Poisoning Attack to G.pdf",
        "data/papers/neurips/2019/da54dd5a0398011cdfa50d559c2c0ef8_Distribution oblivious, risk-aware algorithms for .pdf",
        "data/papers/neurips/2020/21d144c75af2c3a1cb90441bbb7d8b40_Optimal Private Median Estimation under Minimal Di.pdf",
        "data/papers/neurips/2020/30f0641c041f03d94e95a76b9d8bd58f_Reverse-engineering recurrent neural network solut.pdf",
        "data/papers/neurips/2020/6fd9a99a5abed788d9afc9d52d54e91b_Approximate Cross-Validation with Low-Rank Data in.pdf",
        "data/papers/neurips/2020/82674fc29bc0d9895cee346548c2cb5c_Instance-based Generalization in Reinforcement Lea.pdf",
        "data/papers/neurips/2020/9d702ffd99ad9c70ac37e506facc8c38_Efficient Learning of Discrete Graphical Models.pdf",
        "data/papers/neurips/2020/b8b9c74ac526fffbeb2d39ab038d1cd7_Batched Coarse Ranking in Multi-Armed Bandits.pdf",
        "data/papers/neurips/2021/250dd56814ad7c50971ee4020519c6f5_Robust Online Correlation Clustering.pdf",
        "data/papers/neurips/2021/2c7f9ccb5a39073e24babc3a4cb45e60_Scalable Thompson Sampling using Sparse Gaussian P.pdf",
        "data/papers/neurips/2021/498f2c21688f6451d9f5fd09d53edda7_Raw Nav-merge Seismic Data to Subsurface Propertie.pdf",
        "data/papers/neurips/2021/58b7483ba899e0ce4d97ac5eecf6fa99_Asymptotics of the Bootstrap via Stability with Ap.pdf",
        "data/papers/neurips/2021/8da57fac3313174128cc5f13328d4573_Learning to Time-Decode in Spiking Neural Networks.pdf",
        "data/papers/neurips/2021/8ea1e4f9f24c38f168d538c9cfc50a14_On the Representation Power of Set Pooling Network.pdf",
        "data/papers/neurips/2021/b538f279cb2ca36268b23f557a831508_CoFrNets_ Interpretable Neural Architecture Inspir.pdf",
        "data/papers/neurips/2021/b91a76b0b2fa7ce160212f53f3d2edba_Unifying lower bounds on prediction dimension of c.pdf",
        "data/papers/neurips/2021/bd33f02c4e28615b5af2d24703e066d5_Bandits with many optimal arms.pdf",
        "data/papers/neurips/2021/bf65417dcecc7f2b0006e1f5793b7143_Double_Debiased Machine Learning for Dynamic Treat.pdf",
        "data/papers/neurips/2021/c26820b8a4c1b3c2aa868d6d57e14a79_Optimal Policies Tend To Seek Power.pdf",
        "data/papers/neurips/2021/e13748298cfb23c19fdfd134a2221e7b_Rank Overspecified Robust Matrix Recovery_ Subgrad.pdf",
        "data/papers/neurips/2021/fb647ca6672b0930e9d00dc384d8b16f_Batched Thompson Sampling.pdf",
        "data/papers/neurips/2021/fe87435d12ef7642af67d9bc82a8b3cd_Adversarial Examples Make Strong Poisons.pdf",
        "data/papers/neurips/2022/08f9de0232c0b485110237f6e6cf88f1_Predictive Coding beyond Gaussian Distributions.pdf",
        "data/papers/neurips/2022/14da7aea05debb963b3d8d46449d51a0_Integral Probability Metrics PAC-Bayes Bounds.pdf",
        "data/papers/neurips/2022/1687466683649e8bdcdec0e3f5c8de64_DGD^2_ A Linearly Convergent Distributed Algorithm.pdf",
        "data/papers/neurips/2022/1bd6f17639876b4856026744932ec76f_Redundancy-Free Message Passing for Graph Neural N.pdf",
        "data/papers/neurips/2022/1d8f05e4da49a4e1e1b052a3046bceac_UnfoldML_ Cost-Aware and Uncertainty-Based Dynamic.pdf",
        "data/papers/neurips/2022/1fd4367793bcd3ad38a0b820fcc1b815_One for All_ Simultaneous Metric and Preference Le.pdf",
        "data/papers/neurips/2022/22fb65e39d318c4b5b56fbe9cb082e3f_MTNeuro_  A Benchmark for Evaluating Representatio.pdf",
        "data/papers/neurips/2022/3d3a9e085540c65dd3e5731361f9320e_Learning sparse features can lead to overfitting i.pdf",
        "data/papers/neurips/2022/3daf673aa4a06eec9b343686d88333c7_Is this the Right Neighborhood_ Accurate and Query.pdf",
        "data/papers/neurips/2022/b31aec087b4c9be97d7148dfdf6e062d_Towards Reasonable Budget Allocation in Untargeted.pdf",
        "data/papers/neurips/2022/d1422213c9f2bdd5178b77d166fba86a_Differentially Private Online-to-batch for Smooth .pdf",
        "data/papers/neurips/2022/d903c4bb4e77f5de1ec92da2cf9dc8db_Fast Stochastic Composite Minimization and an Acce.pdf",
        "data/papers/neurips/2022/e536e43b01a4387a2282c2b04103c802_Model-based RL with Optimistic Posterior Sampling_.pdf",
        "data/papers/neurips/2022/ef0c1457c4f31c00f460d55ab9d130ed_Acceleration in Distributed Sparse Regression.pdf",
        "data/papers/neurips/2023/4b5d47949866d06ab5c03022b4a5a551_ReDS_ Offline RL With Heteroskedastic Datasets via.pdf",
        "data/papers/neurips/2023/585e9cf25585612ac27b535457116513_On the Importance of Feature Separability in Predi.pdf",
        "data/papers/neurips/2023/7319b7561ffe5e2f6419acd4a2f52d6b_Sharp Calibrated Gaussian Processes.pdf",
        "data/papers/neurips/2023/e85454a113e8b41e017c81875ae68d47_Swarm Reinforcement Learning for Adaptive Mesh Ref.pdf",
        "data/papers/neurips/2024/2e43584b7d7b32fb6b2aa83b32dbbb20_LINGOLY_ A Benchmark of Olympiad-Level Linguistic .pdf",
        "data/papers/neurips/2024/f6adf61977467560f79b95485d1f3a79_Introducing Spectral Attention for Long-Range Depe.pdf",
        "data/papers/neurips/2025/JenfC3ovzU_Amortized Sampling with Transferable Normalizing F.pdf",
        "data/papers/uai/2017/32_Provable Inductive Robust PCA via Iterative Hard T.pdf",
        "data/papers/uai/2019/galy-fajou20a_Multi-Class Gaussian Process Classification Made C.pdf",
        "data/papers/uai/2020/balcan20a_Semi-bandit Optimization in the Dispersed Setting.pdf",
        "data/papers/cvpr/2026/Wu_Computational_Speckle_Pattern_Interferometry_CVPR_2026_paper_Computational Speckle Pattern Interferometry.pdf"
    ]

    @classmethod
    def get_pdf_dir(cls, conference, year=None):
        """Get PDF directory for a conference and optional year"""
        if year:
            return cls.PDF_BASE_DIR / conference / str(year)
        return cls.PDF_BASE_DIR / conference

    @classmethod
    def get_output_dir(cls, conference, year=None):
        """Get output directory for a conference and optional year"""
        if year:
            return cls.NOUGAT_OUTPUT_BASE / conference / str(year)
        return cls.NOUGAT_OUTPUT_BASE / conference

    @classmethod
    def validate_conference(cls, conference):
        """Validate if conference is supported"""
        return conference.lower() in cls.CONFERENCES
